package com.clinevo.smartinbox.service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import com.clinevo.smartinbox.ai.AiClient;
import com.clinevo.smartinbox.repo.InboxRepository;
import com.fasterxml.jackson.databind.JsonNode;

@Service
public class JobWorker {

	private static final Logger log = LoggerFactory.getLogger(JobWorker.class);

	private final InboxRepository repo;
	private final AiClient aiClient;

	public JobWorker(InboxRepository repo, AiClient aiClient) {
		this.repo = repo;
		this.aiClient = aiClient;
	}

	@EventListener(ApplicationReadyEvent.class)
	public void requeueFailedOnStartup() {
		int n = repo.requeueFailedJobs();
		if (n > 0) {
			log.info("Requeued {} failed jobs", n);
		}
	}

	@Scheduled(fixedDelayString = "${inbox.job.poll-ms:5000}")
	public void drain() {
		List<Map<String, Object>> jobs = repo.findPendingJobs(1);
		for (Map<String, Object> job : jobs) {
			long jobId = ((Number) job.get("JOB_ID")).longValue();
			long messageId = ((Number) job.get("MESSAGE_ID")).longValue();
			process(jobId, messageId);
		}
	}

	public void process(long jobId, long messageId) {
		repo.markJobProcessing(jobId);
		repo.updateMessageStatus(messageId, "PROCESSING");
		repo.logAiEvent(messageId, jobId, "JOB_STARTED", "Calling Python AI service");
		long t0 = Instant.now().toEpochMilli();
		try {
			Map<String, Object> msg = repo.getMessage(messageId);
			List<Map<String, Object>> atts = repo.listAttachments(messageId);
			List<Map<String, Object>> pdfs = new ArrayList<>();
			for (Map<String, Object> att : atts) {
				boolean pdf = ((Number) att.get("IS_PDF")).intValue() == 1;
				if (!pdf) {
					continue;
				}
				Map<String, Object> item = new HashMap<>();
				item.put("id", ((Number) att.get("ID")).longValue());
				item.put("filename", str(att.get("FILENAME")));
				item.put("path", str(att.get("STORED_PATH")));
				item.put("mime", str(att.get("MIME_TYPE")));
				pdfs.add(item);
			}
			JsonNode result = aiClient.analyze(messageId, str(msg.get("SENDER")), str(msg.get("SUBJECT")),
					str(msg.get("BODY_TEXT")), String.valueOf(msg.get("RECEIVED_AT")), pdfs);
			persistResult(messageId, result);
			long duration = Instant.now().toEpochMilli() - t0;
			if (result.has("duration_ms") && result.get("duration_ms").canConvertToLong()) {
				duration = result.get("duration_ms").asLong();
			}
			repo.markJobDone(jobId, duration);
			repo.updateMessageStatus(messageId, "DONE");
			repo.logAiEvent(messageId, jobId, "JOB_DONE", "duration_ms=" + duration);
		} catch (Exception e) {
			log.error("Job {} failed", jobId, e);
			repo.markJobFailed(jobId, e.getMessage());
			repo.updateMessageStatus(messageId, "FAILED");
			repo.logAiEvent(messageId, jobId, "JOB_FAILED", e.toString());
		}
	}

	private void persistResult(long messageId, JsonNode result) {
		if (result.has("classifications")) {
			for (JsonNode c : result.get("classifications")) {
				repo.insertClassification(messageId, text(c, "category"), num(c, "confidence"), text(c, "reason"),
						"AI");
			}
		}
		if (result.has("fields")) {
			for (JsonNode f : result.get("fields")) {
				Long attId = f.hasNonNull("attachment_id") ? f.get("attachment_id").asLong() : null;
				Integer page = f.hasNonNull("page_no") ? f.get("page_no").asInt() : null;
				repo.insertField(messageId, text(f, "group"), text(f, "name"), text(f, "value"), num(f, "confidence"),
						text(f, "source_type"), attId, page, text(f, "quote_snippet"));
			}
		}
		if (result.has("pdf_analyses")) {
			for (JsonNode p : result.get("pdf_analyses")) {
				long attId = p.get("attachment_id").asLong();
				Long duration = p.hasNonNull("duration_ms") ? p.get("duration_ms").asLong() : null;
				long analysisId = repo.insertPdfAnalysis(messageId, attId, text(p, "flavor"), text(p, "language"),
						text(p, "original_excerpt"), text(p, "english_text"), text(p, "summary_text"),
						text(p, "relevance_note"), num(p, "ocr_confidence"), duration);
				if (p.has("tables")) {
					for (JsonNode t : p.get("tables")) {
						Integer page = t.hasNonNull("page_no") ? t.get("page_no").asInt() : null;
						repo.insertTable(analysisId, attId, page, t.has("table_json") ? t.get("table_json").toString()
								: text(t, "rows"));
					}
				}
				if (p.has("images")) {
					for (JsonNode im : p.get("images")) {
						Integer page = im.hasNonNull("page_no") ? im.get("page_no").asInt() : null;
						boolean needs = im.path("needs_review").asBoolean(true);
						repo.insertImageFlag(analysisId, attId, page, text(im, "description"), needs);
					}
				}
				repo.markAttachmentProcessed(attId);
			}
		}
	}

	private static String str(Object o) {
		return o == null ? "" : o.toString();
	}

	private static String text(JsonNode n, String field) {
		JsonNode v = n.get(field);
		return v == null || v.isNull() ? null : v.asText();
	}

	private static Double num(JsonNode n, String field) {
		JsonNode v = n.get(field);
		return v == null || v.isNull() ? null : v.asDouble();
	}
}
