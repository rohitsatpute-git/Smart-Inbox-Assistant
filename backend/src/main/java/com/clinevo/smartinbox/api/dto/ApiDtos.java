package com.clinevo.smartinbox.api.dto;

import java.time.LocalDateTime;
import java.util.List;

public final class ApiDtos {

	private ApiDtos() {
	}

	public record MessageSummary(
			long id,
			String sender,
			String subject,
			LocalDateTime receivedAt,
			String status,
			List<ClassificationDto> classifications,
			String summaryPreview,
			Long durationMs) {
	}

	public record MessageDetail(
			long id,
			String sender,
			String subject,
			LocalDateTime receivedAt,
			String bodyText,
			String status,
			List<AttachmentDto> attachments,
			List<ClassificationDto> classifications,
			List<ExtractedFieldDto> fields,
			List<PdfAnalysisDto> pdfAnalyses,
			List<ReviewActionDto> reviews,
			Long durationMs) {
	}

	public record AttachmentDto(
			long id,
			String filename,
			String mimeType,
			boolean pdf,
			boolean processed) {
	}

	public record ClassificationDto(
			long id,
			String category,
			Double confidence,
			String reason,
			String source) {
	}

	public record ExtractedFieldDto(
			long id,
			String group,
			String name,
			String value,
			Double confidence,
			String sourceType,
			Long attachmentId,
			Integer pageNo,
			String quoteSnippet) {
	}

	public record PdfAnalysisDto(
			long id,
			long attachmentId,
			String flavor,
			String language,
			String originalExcerpt,
			String englishText,
			String summaryText,
			String relevanceNote,
			Double ocrConfidence,
			Long durationMs,
			List<TableExtractDto> tables,
			List<ImageFlagDto> images) {
	}

	public record TableExtractDto(long id, Integer pageNo, String tableJson) {
	}

	public record ImageFlagDto(long id, Integer pageNo, String description, boolean needsReview) {
	}

	public record ReviewActionDto(
			long id,
			String actionType,
			String reviewer,
			String reason,
			LocalDateTime createdAt) {
	}

	public record ReviewRequest(
			String actionType,
			String reason,
			List<ClassificationDto> classifications,
			List<ExtractedFieldDto> fields) {
	}

	public record IngestRequest(
			String sender,
			String subject,
			String body,
			List<String> pdfRelativePaths) {
	}
}
