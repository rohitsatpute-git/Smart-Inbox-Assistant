package com.clinevo.smartinbox.ai;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import com.clinevo.smartinbox.config.InboxProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class AiClient {

	private final RestClient restClient;
	private final ObjectMapper mapper;

	public AiClient(InboxProperties properties, ObjectMapper mapper) {
		this.mapper = mapper;
		HttpClient httpClient = HttpClient.newBuilder()
				.version(HttpClient.Version.HTTP_1_1)
				.connectTimeout(Duration.ofSeconds(30))
				.build();
		JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
		factory.setReadTimeout(Duration.ofMinutes(6));
		this.restClient = RestClient.builder()
				.baseUrl(properties.getAiServiceUrl())
				.requestFactory(factory)
				.build();
	}

	public JsonNode analyze(long messageId, String sender, String subject, String body, String receivedAt,
			List<Map<String, Object>> attachments) {
		Map<String, Object> payload = new HashMap<>();
		payload.put("message_id", messageId);
		payload.put("sender", sender);
		payload.put("subject", subject);
		payload.put("body", body);
		payload.put("received_at", receivedAt);
		payload.put("attachments", attachments);
		try {
			String json = restClient.post()
					.uri("/v1/analyze")
					.contentType(MediaType.APPLICATION_JSON)
					.body(mapper.writeValueAsString(payload))
					.retrieve()
					.body(String.class);
			return mapper.readTree(json);
		} catch (Exception e) {
			throw new IllegalStateException("AI service call failed", e);
		}
	}
}
