package com.clinevo.smartinbox.api;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Clob;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.clinevo.smartinbox.api.dto.ApiDtos.AttachmentDto;
import com.clinevo.smartinbox.api.dto.ApiDtos.ClassificationDto;
import com.clinevo.smartinbox.api.dto.ApiDtos.ExtractedFieldDto;
import com.clinevo.smartinbox.api.dto.ApiDtos.ImageFlagDto;
import com.clinevo.smartinbox.api.dto.ApiDtos.IngestRequest;
import com.clinevo.smartinbox.api.dto.ApiDtos.MessageDetail;
import com.clinevo.smartinbox.api.dto.ApiDtos.MessageSummary;
import com.clinevo.smartinbox.api.dto.ApiDtos.PdfAnalysisDto;
import com.clinevo.smartinbox.api.dto.ApiDtos.ReviewActionDto;
import com.clinevo.smartinbox.api.dto.ApiDtos.ReviewRequest;
import com.clinevo.smartinbox.api.dto.ApiDtos.TableExtractDto;
import com.clinevo.smartinbox.config.InboxProperties;
import com.clinevo.smartinbox.repo.InboxRepository;
import com.clinevo.smartinbox.service.IngestService;
import com.clinevo.smartinbox.service.IngestService.SavedFile;
import com.fasterxml.jackson.databind.ObjectMapper;

@RestController
@RequestMapping("/api")
public class MessageController {

	private final InboxRepository repo;
	private final IngestService ingestService;
	private final InboxProperties properties;
	private final ObjectMapper mapper;

	public MessageController(InboxRepository repo, IngestService ingestService, InboxProperties properties,
			ObjectMapper mapper) {
		this.repo = repo;
		this.ingestService = ingestService;
		this.properties = properties;
		this.mapper = mapper;
	}

	@GetMapping("/messages")
	public List<MessageSummary> list() {
		List<MessageSummary> out = new ArrayList<>();
		for (Map<String, Object> row : repo.listMessages()) {
			long id = ((Number) row.get("ID")).longValue();
			List<ClassificationDto> cls = mapClassifications(repo.listClassifications(id));
			String preview = null;
			List<Map<String, Object>> pdfs = repo.listPdfAnalyses(id);
			if (!pdfs.isEmpty()) {
				preview = clob(pdfs.get(0).get("SUMMARY_TEXT"));
				if (preview != null && preview.length() > 280) {
					preview = preview.substring(0, 280) + "…";
				}
			}
			out.add(new MessageSummary(id, str(row.get("SENDER")), str(row.get("SUBJECT")), ts(row.get("RECEIVED_AT")),
					str(row.get("STATUS")), cls, preview, repo.latestJobDuration(id)));
		}
		return out;
	}

	@GetMapping("/messages/{id}")
	public MessageDetail get(@PathVariable long id) {
		Map<String, Object> row = repo.getMessage(id);
		List<AttachmentDto> atts = new ArrayList<>();
		for (Map<String, Object> a : repo.listAttachments(id)) {
			atts.add(new AttachmentDto(((Number) a.get("ID")).longValue(), str(a.get("FILENAME")), str(a.get("MIME_TYPE")),
					num(a.get("IS_PDF")) == 1, num(a.get("PROCESSED_FLAG")) == 1));
		}
		List<PdfAnalysisDto> analyses = new ArrayList<>();
		for (Map<String, Object> p : repo.listPdfAnalyses(id)) {
			long pid = ((Number) p.get("ID")).longValue();
			List<TableExtractDto> tables = new ArrayList<>();
			for (Map<String, Object> t : repo.listTables(pid)) {
				tables.add(new TableExtractDto(((Number) t.get("ID")).longValue(), intOrNull(t.get("PAGE_NO")),
						clob(t.get("TABLE_JSON"))));
			}
			List<ImageFlagDto> images = new ArrayList<>();
			for (Map<String, Object> im : repo.listImages(pid)) {
				images.add(new ImageFlagDto(((Number) im.get("ID")).longValue(), intOrNull(im.get("PAGE_NO")),
						clob(im.get("DESCRIPTION")), num(im.get("NEEDS_REVIEW")) == 1));
			}
			analyses.add(new PdfAnalysisDto(pid, ((Number) p.get("ATTACHMENT_ID")).longValue(), str(p.get("FLAVOR")),
					str(p.get("LANGUAGE")), clob(p.get("ORIGINAL_EXCERPT")), clob(p.get("ENGLISH_TEXT")),
					clob(p.get("SUMMARY_TEXT")), str(p.get("RELEVANCE_NOTE")), dbl(p.get("OCR_CONFIDENCE")),
					longOrNull(p.get("DURATION_MS")), tables, images));
		}
		List<ReviewActionDto> reviews = new ArrayList<>();
		for (Map<String, Object> r : repo.listReviews(id)) {
			reviews.add(new ReviewActionDto(((Number) r.get("ID")).longValue(), str(r.get("ACTION_TYPE")),
					str(r.get("REVIEWER")), str(r.get("REASON")), ts(r.get("CREATED_AT"))));
		}
		return new MessageDetail(id, str(row.get("SENDER")), str(row.get("SUBJECT")), ts(row.get("RECEIVED_AT")),
				clob(row.get("BODY_TEXT")), str(row.get("STATUS")), atts, mapClassifications(repo.listClassifications(id)),
				mapFields(repo.listFields(id)), analyses, reviews, repo.latestJobDuration(id));
	}

	@PostMapping("/messages/{id}/review")
	public MessageDetail review(@PathVariable long id, @RequestBody ReviewRequest request, Authentication auth)
			throws Exception {
		String reviewer = auth == null ? "reviewer" : auth.getName();
		String oldPayload = mapper.writeValueAsString(Map.of(
				"classifications", mapClassifications(repo.listClassifications(id)),
				"fields", mapFields(repo.listFields(id))));
		String action = request.actionType() == null ? "ACCEPT" : request.actionType().toUpperCase();
		if ("OVERRIDE".equals(action)) {
			if (request.reason() == null || request.reason().isBlank()) {
				throw new IllegalArgumentException("Override requires a reason");
			}
			if (request.classifications() != null) {
				repo.deleteClassifications(id);
				for (ClassificationDto c : request.classifications()) {
					repo.insertClassification(id, c.category(), c.confidence(), c.reason(), "REVIEWER");
				}
			}
			if (request.fields() != null) {
				repo.deleteFields(id);
				for (ExtractedFieldDto f : request.fields()) {
					repo.insertField(id, f.group(), f.name(), f.value(), f.confidence(), f.sourceType(),
							f.attachmentId(), f.pageNo(), f.quoteSnippet());
				}
			}
		}
		repo.insertReview(id, action, reviewer, request.reason(), oldPayload, mapper.writeValueAsString(request));
		repo.updateMessageStatus(id, "REVIEWED");
		repo.logAiEvent(id, null, "REVIEW_" + action, reviewer + ": " + request.reason());
		return get(id);
	}

	@PostMapping("/ingest")
	public Map<String, Object> ingest(@RequestBody IngestRequest request) throws IOException {
		List<SavedFile> files = new ArrayList<>();
		Path testdata = Path.of(properties.getTestdataDir()).toAbsolutePath().normalize();
		if (request.pdfRelativePaths() != null) {
			for (String rel : request.pdfRelativePaths()) {
				Path src = testdata.resolve(rel).normalize();
				if (!src.startsWith(testdata) || !Files.exists(src)) {
					continue;
				}
				Path stored = ingestService.copyToStore(src.getFileName().toString(), Files.readAllBytes(src));
				files.add(new SavedFile(src.getFileName().toString(), "application/pdf", stored.toString()));
			}
		}
		long id = ingestService.ingest(null, request.sender(), request.subject(), LocalDateTime.now(), request.body(),
				files);
		return Map.of("id", id, "status", "queued");
	}

	@PostMapping("/demo/load-samples")
	public Map<String, Object> loadSamples() throws IOException {
		Path manifest = Path.of(properties.getTestdataDir()).toAbsolutePath().normalize().resolve("manifest.json");
		if (!Files.exists(manifest)) {
			return Map.of("loaded", 0, "error", "testdata/manifest.json not found — run scripts/generate_testdata.py");
		}
		var root = mapper.readTree(Files.readString(manifest));
		int n = 0;
		for (var item : root.withArray("messages")) {
			IngestRequest req = mapper.treeToValue(item, IngestRequest.class);
			ingest(req);
			n++;
		}
		return Map.of("loaded", n);
	}

	@GetMapping("/attachments/{id}/file")
	public ResponseEntity<Resource> file(@PathVariable long id) {
		Map<String, Object> att = repo.getAttachment(id);
		Path path = Path.of(str(att.get("STORED_PATH")));
		Resource resource = new FileSystemResource(path);
		return ResponseEntity.ok()
				.header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + str(att.get("FILENAME")) + "\"")
				.contentType(MediaType.APPLICATION_PDF)
				.body(resource);
	}

	private List<ClassificationDto> mapClassifications(List<Map<String, Object>> rows) {
		List<ClassificationDto> out = new ArrayList<>();
		for (Map<String, Object> c : rows) {
			out.add(new ClassificationDto(((Number) c.get("ID")).longValue(), str(c.get("CATEGORY")),
					dbl(c.get("CONFIDENCE")), str(c.get("REASON")), str(c.get("SOURCE"))));
		}
		return out;
	}

	private List<ExtractedFieldDto> mapFields(List<Map<String, Object>> rows) {
		List<ExtractedFieldDto> out = new ArrayList<>();
		for (Map<String, Object> f : rows) {
			out.add(new ExtractedFieldDto(((Number) f.get("ID")).longValue(), str(f.get("FIELD_GROUP")),
					str(f.get("FIELD_NAME")), clob(f.get("FIELD_VALUE")), dbl(f.get("CONFIDENCE")),
					str(f.get("SOURCE_TYPE")), longOrNull(f.get("ATTACHMENT_ID")), intOrNull(f.get("PAGE_NO")),
					str(f.get("QUOTE_SNIPPET"))));
		}
		return out;
	}

	private static String str(Object o) {
		return o == null ? null : o.toString();
	}

	private static int num(Object o) {
		return o == null ? 0 : ((Number) o).intValue();
	}

	private static Double dbl(Object o) {
		return o == null ? null : ((Number) o).doubleValue();
	}

	private static Long longOrNull(Object o) {
		return o == null ? null : ((Number) o).longValue();
	}

	private static Integer intOrNull(Object o) {
		return o == null ? null : ((Number) o).intValue();
	}

	private static LocalDateTime ts(Object o) {
		if (o instanceof Timestamp t) {
			return t.toLocalDateTime();
		}
		return null;
	}

	private static String clob(Object o) {
		if (o == null) {
			return null;
		}
		if (o instanceof Clob c) {
			try {
				return c.getSubString(1, (int) c.length());
			} catch (Exception e) {
				return null;
			}
		}
		return o.toString();
	}
}
