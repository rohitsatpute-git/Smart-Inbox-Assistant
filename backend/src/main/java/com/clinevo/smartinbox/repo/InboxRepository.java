package com.clinevo.smartinbox.repo;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.simple.SimpleJdbcInsert;
import org.springframework.stereotype.Repository;

@Repository
public class InboxRepository {

	private final JdbcTemplate jdbc;
	private final SimpleJdbcInsert messageInsert;
	private final SimpleJdbcInsert attachmentInsert;
	private final SimpleJdbcInsert jobInsert;

	public InboxRepository(JdbcTemplate jdbc) {
		this.jdbc = jdbc;
		this.messageInsert = new SimpleJdbcInsert(jdbc).withTableName("INBOX_MESSAGE").usingGeneratedKeyColumns("ID")
				.usingColumns("GMAIL_UID", "SENDER", "SUBJECT", "RECEIVED_AT", "BODY_TEXT", "STATUS");
		this.attachmentInsert = new SimpleJdbcInsert(jdbc).withTableName("ATTACHMENT").usingGeneratedKeyColumns("ID")
				.usingColumns("MESSAGE_ID", "FILENAME", "MIME_TYPE", "STORED_PATH", "IS_PDF", "PROCESSED_FLAG");
		this.jobInsert = new SimpleJdbcInsert(jdbc).withTableName("PROCESSING_JOB").usingGeneratedKeyColumns("ID")
				.usingColumns("MESSAGE_ID", "STATUS");
	}

	public boolean existsByGmailUid(String uid) {
		Integer n = jdbc.queryForObject("SELECT COUNT(*) FROM inbox_message WHERE gmail_uid = ?", Integer.class, uid);
		return n != null && n > 0;
	}

	public long insertMessage(String uid, String sender, String subject, LocalDateTime receivedAt, String body,
			String status) {
		Number id = messageInsert.executeAndReturnKey(new MapSqlParameterSource()
				.addValue("GMAIL_UID", uid)
				.addValue("SENDER", sender)
				.addValue("SUBJECT", subject)
				.addValue("RECEIVED_AT", Timestamp.valueOf(receivedAt))
				.addValue("BODY_TEXT", body)
				.addValue("STATUS", status));
		return id.longValue();
	}

	public long insertAttachment(long messageId, String filename, String mime, String path, boolean pdf) {
		Number id = attachmentInsert.executeAndReturnKey(new MapSqlParameterSource()
				.addValue("MESSAGE_ID", messageId)
				.addValue("FILENAME", filename)
				.addValue("MIME_TYPE", mime)
				.addValue("STORED_PATH", path)
				.addValue("IS_PDF", pdf ? 1 : 0)
				.addValue("PROCESSED_FLAG", 0));
		return id.longValue();
	}

	public long insertJob(long messageId) {
		Number id = jobInsert.executeAndReturnKey(new MapSqlParameterSource()
				.addValue("MESSAGE_ID", messageId)
				.addValue("STATUS", "PENDING"));
		return id.longValue();
	}

	public void updateMessageStatus(long messageId, String status) {
		jdbc.update("UPDATE inbox_message SET status = ? WHERE id = ?", status, messageId);
	}

	public List<Map<String, Object>> findPendingJobs(int limit) {
		return jdbc.queryForList("""
				SELECT j.id AS job_id, j.message_id
				FROM processing_job j
				WHERE j.status = 'PENDING'
				ORDER BY j.id
				FETCH FIRST ? ROWS ONLY
				""", limit);
	}

	public void markJobProcessing(long jobId) {
		jdbc.update("UPDATE processing_job SET status = 'PROCESSING', started_at = SYSTIMESTAMP WHERE id = ?", jobId);
	}

	public void markJobDone(long jobId, long durationMs) {
		jdbc.update(
				"UPDATE processing_job SET status = 'DONE', finished_at = SYSTIMESTAMP, duration_ms = ? WHERE id = ?",
				durationMs, jobId);
	}

	public void markJobFailed(long jobId, String error) {
		jdbc.update(
				"UPDATE processing_job SET status = 'FAILED', finished_at = SYSTIMESTAMP, error_text = ? WHERE id = ?",
				error, jobId);
	}

	public int requeueFailedJobs() {
		int jobs = jdbc.update("""
				UPDATE processing_job
				SET status = 'PENDING', error_text = NULL, started_at = NULL, finished_at = NULL, duration_ms = NULL
				WHERE status = 'FAILED'
				""");
		jdbc.update("UPDATE inbox_message SET status = 'PENDING' WHERE status = 'FAILED'");
		return jobs;
	}

	public Map<String, Object> getMessage(long id) {
		return jdbc.queryForMap("SELECT * FROM inbox_message WHERE id = ?", id);
	}

	public List<Map<String, Object>> listMessages() {
		return jdbc.queryForList("SELECT * FROM inbox_message ORDER BY received_at DESC NULLS LAST, id DESC");
	}

	public List<Map<String, Object>> listAttachments(long messageId) {
		return jdbc.queryForList("SELECT * FROM attachment WHERE message_id = ? ORDER BY id", messageId);
	}

	public Map<String, Object> getAttachment(long id) {
		return jdbc.queryForMap("SELECT * FROM attachment WHERE id = ?", id);
	}

	public List<Map<String, Object>> listClassifications(long messageId) {
		return jdbc.queryForList("SELECT * FROM classification WHERE message_id = ? ORDER BY id", messageId);
	}

	public List<Map<String, Object>> listFields(long messageId) {
		return jdbc.queryForList("SELECT * FROM extracted_field WHERE message_id = ? ORDER BY id", messageId);
	}

	public List<Map<String, Object>> listPdfAnalyses(long messageId) {
		return jdbc.queryForList("SELECT * FROM pdf_analysis WHERE message_id = ? ORDER BY id", messageId);
	}

	public List<Map<String, Object>> listTables(long pdfAnalysisId) {
		return jdbc.queryForList("SELECT * FROM table_extract WHERE pdf_analysis_id = ? ORDER BY id", pdfAnalysisId);
	}

	public List<Map<String, Object>> listImages(long pdfAnalysisId) {
		return jdbc.queryForList("SELECT * FROM image_flag WHERE pdf_analysis_id = ? ORDER BY id", pdfAnalysisId);
	}

	public List<Map<String, Object>> listReviews(long messageId) {
		return jdbc.queryForList("SELECT * FROM review_action WHERE message_id = ? ORDER BY id DESC", messageId);
	}

	public Long latestJobDuration(long messageId) {
		List<Long> rows = jdbc.query(
				"SELECT duration_ms FROM processing_job WHERE message_id = ? ORDER BY id DESC FETCH FIRST 1 ROWS ONLY",
				(rs, i) -> rs.getObject(1) == null ? null : rs.getLong(1), messageId);
		return rows.isEmpty() ? null : rows.get(0);
	}

	public void deleteClassifications(long messageId) {
		jdbc.update("DELETE FROM classification WHERE message_id = ?", messageId);
	}

	public void deleteFields(long messageId) {
		jdbc.update("DELETE FROM extracted_field WHERE message_id = ?", messageId);
	}

	public void insertClassification(long messageId, String category, Double confidence, String reason, String source) {
		jdbc.update(
				"INSERT INTO classification (message_id, category, confidence, reason, source) VALUES (?,?,?,?,?)",
				messageId, category, confidence, reason, source);
	}

	public void insertField(long messageId, String group, String name, String value, Double confidence,
			String sourceType, Long attachmentId, Integer pageNo, String quote) {
		jdbc.update("""
				INSERT INTO extracted_field
				(message_id, field_group, field_name, field_value, confidence, source_type, attachment_id, page_no, quote_snippet)
				VALUES (?,?,?,?,?,?,?,?,?)
				""", messageId, group, name, value, confidence, sourceType, attachmentId, pageNo, quote);
	}

	public long insertPdfAnalysis(long messageId, long attachmentId, String flavor, String language,
			String originalExcerpt, String englishText, String summary, String relevance, Double ocr, Long durationMs) {
		jdbc.update("""
				INSERT INTO pdf_analysis
				(message_id, attachment_id, flavor, language, original_excerpt, english_text, summary_text, relevance_note, ocr_confidence, duration_ms)
				VALUES (?,?,?,?,?,?,?,?,?,?)
				""", messageId, attachmentId, flavor, language, originalExcerpt, englishText, summary, relevance, ocr,
				durationMs);
		return jdbc.queryForObject("SELECT MAX(id) FROM pdf_analysis WHERE attachment_id = ?", Long.class, attachmentId);
	}

	public void insertTable(long pdfAnalysisId, long attachmentId, Integer pageNo, String json) {
		jdbc.update(
				"INSERT INTO table_extract (pdf_analysis_id, attachment_id, page_no, table_json) VALUES (?,?,?,?)",
				pdfAnalysisId, attachmentId, pageNo, json);
	}

	public void insertImageFlag(long pdfAnalysisId, long attachmentId, Integer pageNo, String description,
			boolean needsReview) {
		jdbc.update(
				"INSERT INTO image_flag (pdf_analysis_id, attachment_id, page_no, description, needs_review) VALUES (?,?,?,?,?)",
				pdfAnalysisId, attachmentId, pageNo, description, needsReview ? 1 : 0);
	}

	public void markAttachmentProcessed(long attachmentId) {
		jdbc.update("UPDATE attachment SET processed_flag = 1 WHERE id = ?", attachmentId);
	}

	public void insertReview(long messageId, String action, String reviewer, String reason, String oldPayload,
			String newPayload) {
		jdbc.update("""
				INSERT INTO review_action (message_id, action_type, reviewer, reason, old_payload, new_payload)
				VALUES (?,?,?,?,?,?)
				""", messageId, action, reviewer, reason, oldPayload, newPayload);
	}

	public void logAiEvent(Long messageId, Long jobId, String event, String detail) {
		jdbc.update("BEGIN log_ai_event(?,?,?,?); END;", messageId, jobId, event, detail);
	}
}
