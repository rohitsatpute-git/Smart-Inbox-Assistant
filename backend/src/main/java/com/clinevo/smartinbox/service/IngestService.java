package com.clinevo.smartinbox.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.clinevo.smartinbox.config.InboxProperties;
import com.clinevo.smartinbox.repo.InboxRepository;

@Service
public class IngestService {

	private final InboxRepository repo;
	private final InboxProperties properties;

	public IngestService(InboxRepository repo, InboxProperties properties) {
		this.repo = repo;
		this.properties = properties;
	}

	@Transactional
	public long ingest(String uid, String sender, String subject, LocalDateTime receivedAt, String body,
			List<SavedFile> files) {
		if (uid != null && repo.existsByGmailUid(uid)) {
			return -1;
		}
		if (uid == null || uid.isBlank()) {
			uid = "local-" + UUID.randomUUID();
		}
		long messageId = repo.insertMessage(uid, sender, subject, receivedAt, body, "PENDING");
		for (SavedFile file : files) {
			boolean pdf = file.filename().toLowerCase().endsWith(".pdf")
					|| "application/pdf".equalsIgnoreCase(file.mime());
			repo.insertAttachment(messageId, file.filename(), file.mime(), file.storedPath(), pdf);
			if (!pdf) {
				repo.logAiEvent(messageId, null, "NON_PDF_ATTACHMENT", file.filename() + " logged, not processed");
			}
		}
		repo.insertJob(messageId);
		repo.logAiEvent(messageId, null, "INGESTED", "Message stored and queued");
		return messageId;
	}

	public Path copyToStore(String originalName, byte[] bytes) throws IOException {
		Path dir = Path.of(properties.getAttachmentDir()).toAbsolutePath().normalize();
		Files.createDirectories(dir);
		String safe = originalName == null ? "file.bin" : originalName.replaceAll("[^A-Za-z0-9._-]", "_");
		Path dest = dir.resolve(System.currentTimeMillis() + "-" + UUID.randomUUID() + "-" + safe);
		Files.write(dest, bytes);
		return dest;
	}

	public record SavedFile(String filename, String mime, String storedPath) {
	}
}
