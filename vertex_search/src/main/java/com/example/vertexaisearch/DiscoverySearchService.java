package com.example.vertexaisearch;

import com.google.api.gax.core.FixedCredentialsProvider;
import com.google.api.gax.rpc.ApiException;
import com.google.auth.oauth2.GoogleCredentials;
import com.google.cloud.discoveryengine.v1.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Collections;
import java.util.List;

public class DiscoverySearchService implements AutoCloseable {

    private static final Logger logger = LoggerFactory.getLogger(DiscoverySearchService.class);

    private final SearchServiceClient searchServiceClient;
    private final SearchConfig config;

    public DiscoverySearchService(SearchConfig config) throws IOException {
        this.config = config;
        this.searchServiceClient = createClient();
        logger.info("DiscoverySearchService initialized successfully for config: {}", config);
    }

    private SearchServiceClient createClient() throws IOException {
        logger.info("Attempting to create SearchServiceClient...");
        logger.info("Using Service Account Key: {}", config.getServiceAccountKeyPath());
        logger.info("Using PSC Endpoint: {}", config.getPscEndpoint());

        GoogleCredentials credentials;
        try (FileInputStream credentialsStream = new FileInputStream(config.getServiceAccountKeyPath())) {
            credentials = GoogleCredentials.fromStream(credentialsStream)
                    .createScoped(Collections.singletonList("https://www.googleapis.com/auth/cloud-platform"));
            logger.debug("GoogleCredentials loaded successfully from stream.");
        } catch (IOException e) {
            logger.error("Failed to load credentials from path: {}", config.getServiceAccountKeyPath(), e);
            throw e;
        }

        SearchServiceSettings.Builder settingsBuilder = SearchServiceSettings.newBuilder();

        // 1. Configure Credentials
        settingsBuilder.setCredentialsProvider(FixedCredentialsProvider.create(credentials));
        logger.debug("Credentials provider set.");

        // 2. Configure Endpoint for PSC
        // This directs the client to use your private endpoint instead of the public internet endpoint.
        settingsBuilder.setEndpoint(config.getPscEndpoint());
        logger.debug("Endpoint set to: {}", config.getPscEndpoint());

        // Optional: Configure transport channel provider if needed (usually handled by setEndpoint)
        // settingsBuilder.setTransportChannelProvider(...)

        try {
            SearchServiceClient client = SearchServiceClient.create(settingsBuilder.build());
            logger.info("SearchServiceClient created successfully.");
            return client;
        } catch (IOException e) {
            logger.error("Failed to create SearchServiceClient with custom endpoint and credentials", e);
            throw e;
        }
    }

    public SearchResponse performSearch(String query, int pageSize) {
        if (query == null || query.trim().isEmpty()) {
            logger.warn("Search query is null or empty.");
            return SearchResponse.newBuilder().build(); // Return empty response
        }

        String servingConfigName = config.getServingConfigName();
        logger.info("Performing search for query='{}' on serving config='{}' with page size={}", query, servingConfigName, pageSize);

        SearchRequest request =
                SearchRequest.newBuilder()
                        .setServingConfig(servingConfigName)
                        .setQuery(query)
                        .setPageSize(pageSize)
                        // Add other parameters like filters, user info, offset etc. as needed
                        // .setFilter("...")
                        // .setUserInfo(...)
                        // .setOffset(0)
                        .build();

        try {
            SearchResponse response = searchServiceClient.search(request);
            logger.info("Search successful. Found {} total results (showing first {}).", response.getTotalSize(), response.getResultsCount());
            // Log details of first few results for debugging if needed
            if (logger.isDebugEnabled()) {
                 response.getResultsList().stream().limit(5).forEach(result ->
                     logger.debug(" - Result ID: {}, Title: {}",
                        result.getDocument().getId(),
                        result.getDocument().getStructData().getFieldsOrDefault("title", com.google.protobuf.Value.newBuilder().setStringValue("N/A").build()).getStringValue()
                     )
                 );
            }
            return response;
        } catch (ApiException e) {
            logger.error("API Exception during search for query '{}': Status Code = {}, Message = {}", query, e.getStatusCode(), e.getMessage(), e);
            // Consider throwing a custom exception or returning a specific error indicator
            return SearchResponse.newBuilder().build(); // Return empty response on error
        } catch (Exception e) {
            logger.error("Unexpected exception during search for query '{}'", query, e);
            return SearchResponse.newBuilder().build(); // Return empty response on error
        }
    }

    @Override
    public void close() {
        if (searchServiceClient != null) {
            logger.info("Shutting down SearchServiceClient...");
            searchServiceClient.close();
            // Consider adding shutdownNow and awaitTermination for cleaner shutdown
             // searchServiceClient.shutdown();
             // try {
             //     if (!searchServiceClient.awaitTermination(30, TimeUnit.SECONDS)) {
             //         searchServiceClient.shutdownNow();
             //     }
             // } catch (InterruptedException ex) {
             //      searchServiceClient.shutdownNow();
             //      Thread.currentThread().interrupt();
             // }
            logger.info("SearchServiceClient shut down.");
        }
    }
}