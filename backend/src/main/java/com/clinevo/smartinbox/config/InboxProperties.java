package com.clinevo.smartinbox.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "inbox")
public class InboxProperties {

	private String aiServiceUrl = "http://localhost:8000";
	private String attachmentDir = "../data/attachments";
	private String testdataDir = "../testdata";
	private String reviewerUser = "reviewer";
	private String reviewerPassword = "reviewer123";
	private String corsOrigins = "http://localhost:4200,http://127.0.0.1:4200,http://localhost";
	private final Imap imap = new Imap();

	public String getAiServiceUrl() {
		return aiServiceUrl;
	}

	public void setAiServiceUrl(String aiServiceUrl) {
		this.aiServiceUrl = aiServiceUrl;
	}

	public String getAttachmentDir() {
		return attachmentDir;
	}

	public void setAttachmentDir(String attachmentDir) {
		this.attachmentDir = attachmentDir;
	}

	public String getTestdataDir() {
		return testdataDir;
	}

	public void setTestdataDir(String testdataDir) {
		this.testdataDir = testdataDir;
	}

	public String getReviewerUser() {
		return reviewerUser;
	}

	public void setReviewerUser(String reviewerUser) {
		this.reviewerUser = reviewerUser;
	}

	public String getReviewerPassword() {
		return reviewerPassword;
	}

	public void setReviewerPassword(String reviewerPassword) {
		this.reviewerPassword = reviewerPassword;
	}

	public String getCorsOrigins() {
		return corsOrigins;
	}

	public void setCorsOrigins(String corsOrigins) {
		this.corsOrigins = corsOrigins;
	}

	public Imap getImap() {
		return imap;
	}

	public static class Imap {
		private boolean enabled = true;
		private String host = "imap.gmail.com";
		private int port = 993;
		private String user = "";
		private String password = "";
		private long pollMs = 30000;
		private int maxPerPoll = 5;

		public boolean isEnabled() {
			return enabled;
		}

		public void setEnabled(boolean enabled) {
			this.enabled = enabled;
		}

		public String getHost() {
			return host;
		}

		public void setHost(String host) {
			this.host = host;
		}

		public int getPort() {
			return port;
		}

		public void setPort(int port) {
			this.port = port;
		}

		public String getUser() {
			return user;
		}

		public void setUser(String user) {
			this.user = user;
		}

		public String getPassword() {
			return password;
		}

		public void setPassword(String password) {
			this.password = password;
		}

		public long getPollMs() {
			return pollMs;
		}

		public void setPollMs(long pollMs) {
			this.pollMs = pollMs;
		}

		public int getMaxPerPoll() {
			return maxPerPoll;
		}

		public void setMaxPerPoll(int maxPerPoll) {
			this.maxPerPoll = maxPerPoll;
		}
	}
}
