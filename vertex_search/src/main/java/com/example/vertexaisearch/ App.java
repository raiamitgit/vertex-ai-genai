package com.example.vertexaisearch;

import com.google.cloud.discoveryengine.v1.SearchResponse;
import com.google.protobuf.Value;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.Map;
import java.util.Scanner;

public class App {

    private static final Logger logger = LoggerFactory.getLogger(App.class);

    // --- Configuration - Replace with your actual values or load from external source ---
    // ** IMPORTANT **: It's better to load these from environment variables,
    //                  command-line arguments, or a config file in production.
    private static final String GCP_PROJECT_ID = "your-gcp-project-id";
    private static final String LOCATION_ID = "global"; // Or your specific location e.g., "us"
    private static final String ENGINE_ID = "your-search-engine-id"; // Or Data Store ID
    private static final String SERVICE_ACCOUNT_KEY_PATH = "service-account-key.json"; // Relative path
    // ** IMPORTANT **: Replace with your actual PSC endpoint IP/DNS and port (usually 443)
    private static final String PSC_ENDPOINT = "your-psc-ip-or-dns:443";
    // --- End Configuration ---


    public static void main(String[] args) {
        logger.info("Starting Vertex AI Search PSC Application...");

        SearchConfig config = loadConfiguration();
        if (config == null) {
            return; // Exit if config loading fails
        }

        try (DiscoverySearchService searchService = new DiscoverySearchService(config)) {

            // Example: Perform a single search from command line argument
            if (args.length > 0) {
                String query = args[0];
                logger.info("Performing search based on command line argument: '{}'", query);
                executeSearch(searchService, query);
            } else {
                // Example: Interactive search loop
                runInteractiveSearch(searchService);
            }

        } catch (IOException e) {
            logger.error("Failed to initialize DiscoverySearchService: {}", e.getMessage(), e);
        } catch (Exception e) {
            logger.error("An unexpected error occurred: {}", e.getMessage(), e);
        } finally {
            logger.info("Vertex AI Search PSC Application finished.");
        }
    }

    private static SearchConfig loadConfiguration() {
         try {
             // Prioritize environment variables if available
             String projectId = System.getenv().getOrDefault("GCP_PROJECT_ID", GCP_PROJECT_ID);
             String locationId = System.getenv().getOrDefault("LOCATION_ID", LOCATION_ID);
             String engineId = System.getenv().getOrDefault("ENGINE_ID", ENGINE_ID);
             String keyPath = System.getenv().getOrDefault("SERVICE_ACCOUNT_KEY_PATH", SERVICE_ACCOUNT_KEY_PATH);
             String pscEndpoint = System.getenv().getOrDefault("PSC_ENDPOINT", PSC_ENDPOINT);

             // Basic validation (more robust validation is in SearchConfig constructor)
             if (projectId.equals("your-gcp-project-id") || engineId.equals("your-search-engine-id") || pscEndpoint.equals("your-psc-ip-or-dns:443")) {
                 logger.warn("Using default configuration values. Please update App.java or set environment variables (GCP_PROJECT_ID, LOCATION_ID, ENGINE_ID, SERVICE_ACCOUNT_KEY_PATH, PSC_ENDPOINT).");
             }
              if (pscEndpoint.equals("your-psc-ip-or-dns:443")){
                 logger.error("FATAL: PSC_ENDPOINT is not configured. Please update App.java or set the PSC_ENDPOINT environment variable.");
                 return null; // Cannot proceed without PSC endpoint
             }

             return new SearchConfig(projectId, locationId, engineId, keyPath, pscEndpoint);

         } catch (IllegalArgumentException e) {
              logger.error("Invalid configuration: {}", e.getMessage());
              return null;
         }
    }


    private static void runInteractiveSearch(DiscoverySearchService searchService) {
        Scanner scanner = new Scanner(System.in);
        String query;

        System.out.println("\nEnter search query (or type 'exit' to quit):");
        while (true) {
            System.out.print("> ");
            query = scanner.nextLine();

            if (query.equalsIgnoreCase("exit")) {
                break;
            }

            if (!query.trim().isEmpty()) {
                executeSearch(searchService, query);
            } else {
                 System.out.println("Please enter a query.");
            }
             System.out.println("\nEnter search query (or type 'exit' to quit):");
        }
        scanner.close();
        System.out.println("Exiting interactive search.");
    }

    private static void executeSearch(DiscoverySearchService searchService, String query) {
        System.out.println("\nSearching for: '" + query + "'...");
        long startTime = System.currentTimeMillis();

        SearchResponse response = searchService.performSearch(query, 10); // Requesting 10 results

        long duration = System.currentTimeMillis() - startTime;
        System.out.println("Search completed in " + duration + " ms.");

        if (response != null && response.getResultsCount() > 0) {
            System.out.println("Found " + response.getTotalSize() + " total results. Displaying top " + response.getResultsCount() + ":");
            int rank = 1;
            for (SearchResponse.SearchResult result : response.getResultsList()) {
                Document document = result.getDocument();
                // Extract common fields - adjust keys ('title', 'link', 'snippets') based on your data schema
                String title = getStringValue(document.getStructData(), "title", "N/A");
                String link = getStringValue(document.getStructData(), "link", "#"); // Use derivedStructData for generated links if applicable
                String snippet = getSnippet(result); // Extract snippet if available

                System.out.println("\n[" + rank + "] " + title);
                System.out.println("   ID: " + document.getId());
                System.out.println("   Link: " + link);
                if (!snippet.isEmpty()) {
                    System.out.println("   Snippet: " + snippet.replace("\n","\n   "));
                }

                // Optional: Print other fields from document.getStructData() or document.getJsonData()
                // System.out.println("   All Data: " + document.getStructData());

                rank++;
            }
        } else if (response != null) {
            System.out.println("No results found for your query.");
        } else {
            System.out.println("Search failed. Check logs for details.");
        }
    }

    // Helper to safely extract string fields from Struct data
    private static String getStringValue(com.google.protobuf.Struct struct, String key, String defaultValue) {
        if (struct != null && struct.containsFields(key)) {
            Value value = struct.getFieldsOrThrow(key);
            if (value.getKindCase() == Value.KindCase.STRING_VALUE) {
                return value.getStringValue();
            } else if (value.getKindCase() != Value.KindCase.NULL_VALUE) {
                 logger.warn("Field '{}' is not a String value, it's a {}. Returning raw string.", key, value.getKindCase());
                 return value.toString(); // Or handle other types as needed
            }
        }
        return defaultValue;
    }

     // Helper to extract snippets, preferring Document Level Snippets if available
    private static String getSnippet(SearchResponse.SearchResult result) {
        // Check for Document-Level snippets first (often more relevant)
        if (result.getDocument().containsStructData("snippets")) {
            Value snippetsValue = result.getDocument().getStructData().getFieldsOrThrow("snippets");
            if (snippetsValue.getKindCase() == Value.KindCase.LIST_VALUE && snippetsValue.getListValue().getValuesCount() > 0) {
                 // Let's take the first snippet value if it's a struct with a "snippet" field
                 Value firstSnippetEntry = snippetsValue.getListValue().getValues(0);
                 if(firstSnippetEntry.getKindCase() == Value.KindCase.STRUCT_VALUE && firstSnippetEntry.getStructValue().containsFields("snippet")){
                     return firstSnippetEntry.getStructValue().getFieldsOrThrow("snippet").getStringValue();
                 } else if (firstSnippetEntry.getKindCase() == Value.KindCase.STRING_VALUE){
                     // Sometimes the list might contain strings directly
                     return firstSnippetEntry.getStringValue();
                 }
            }
        }
        // Fallback to Extractive Answers / Extractive Segments if needed and configured
        // (Add logic here if you use those features)

        return ""; // No snippet found
    }
}