package com.clinevo.smartinbox.imap;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import com.clinevo.smartinbox.config.InboxProperties;
import com.clinevo.smartinbox.service.IngestService;
import com.clinevo.smartinbox.service.IngestService.SavedFile;

import jakarta.mail.BodyPart;
import jakarta.mail.Flags;
import jakarta.mail.Folder;
import jakarta.mail.Message;
import jakarta.mail.Multipart;
import jakarta.mail.Session;
import jakarta.mail.Store;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeUtility;
import jakarta.mail.search.FlagTerm;

@Component
public class ImapPoller {

	private static final Logger log = LoggerFactory.getLogger(ImapPoller.class);

	private final InboxProperties properties;
	private final IngestService ingestService;

	public ImapPoller(InboxProperties properties, IngestService ingestService) {
		this.properties = properties;
		this.ingestService = ingestService;
	}

	@Scheduled(fixedDelayString = "${inbox.imap.poll-ms:30000}")
	public void poll() {
		InboxProperties.Imap imap = properties.getImap();
		if (!imap.isEnabled() || imap.getUser() == null || imap.getUser().isBlank()) {
			return;
		}
		Properties props = new Properties();
		props.put("mail.store.protocol", "imaps");
		props.put("mail.imaps.host", imap.getHost());
		props.put("mail.imaps.port", String.valueOf(imap.getPort()));
		props.put("mail.imaps.ssl.enable", "true");
		Session session = Session.getInstance(props);
		try (Store store = session.getStore("imaps")) {
			store.connect(imap.getHost(), imap.getPort(), imap.getUser(), imap.getPassword().replace(" ", ""));
			try (Folder inbox = store.getFolder("INBOX")) {
				inbox.open(Folder.READ_WRITE);
				Message[] messages = inbox.search(new FlagTerm(new Flags(Flags.Flag.SEEN), false));
				log.info("IMAP unseen count={}", messages.length);
				for (Message message : messages) {
					try {
						ingestOne(message);
						message.setFlag(Flags.Flag.SEEN, true);
					} catch (Exception e) {
						log.warn("Failed to ingest IMAP message", e);
					}
				}
			}
		} catch (Exception e) {
			log.warn("IMAP poll failed: {}", e.getMessage());
		}
	}

	private void ingestOne(Message message) throws Exception {
		String uid = String.valueOf(message.getFolder().getURLName()) + "-" + message.getMessageNumber() + "-"
				+ (message.getSentDate() == null ? "na" : message.getSentDate().getTime());
		String sender = "";
		if (message.getFrom() != null && message.getFrom().length > 0) {
			sender = InternetAddress.toString(message.getFrom());
		}
		String subject = message.getSubject();
		LocalDateTime received = message.getReceivedDate() == null ? LocalDateTime.now()
				: LocalDateTime.ofInstant(message.getReceivedDate().toInstant(), ZoneId.systemDefault());
		StringBuilder body = new StringBuilder();
		List<SavedFile> files = new ArrayList<>();
		Object content = message.getContent();
		if (content instanceof String text) {
			body.append(text);
		} else if (content instanceof Multipart mp) {
			extractMultipart(mp, body, files);
		}
		ingestService.ingest(uid, sender, subject, received, body.toString(), files);
	}

	private void extractMultipart(Multipart mp, StringBuilder body, List<SavedFile> files) throws Exception {
		for (int i = 0; i < mp.getCount(); i++) {
			BodyPart part = mp.getBodyPart(i);
			if (part.getContent() instanceof Multipart nested) {
				extractMultipart(nested, body, files);
				continue;
			}
			String disp = part.getDisposition();
			String fileName = part.getFileName();
			if (fileName != null || (disp != null && disp.equalsIgnoreCase(BodyPart.ATTACHMENT))) {
				byte[] bytes = part.getInputStream().readAllBytes();
				String name = fileName == null ? "attachment.bin" : MimeUtility.decodeText(fileName);
				var stored = ingestService.copyToStore(name, bytes);
				files.add(new SavedFile(name, part.getContentType(), stored.toString()));
			} else if (part.isMimeType("text/plain")) {
				body.append(part.getContent());
			} else if (part.isMimeType("text/html") && body.isEmpty()) {
				body.append(part.getContent());
			}
		}
	}
}
