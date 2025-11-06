package com.bookmap.demo.consumer.utils;

import java.io.File;
import java.io.IOException;
import java.util.logging.*;

/**
 * Centralized logging configuration for all consumers
 * Creates separate log files for each component with rotation
 */
public class LoggingConfig {
    private static final String LOG_DIR = "F:/Databases/Logs/";
    private static boolean initialized = false;

    /**
     * Initialize logging for a specific consumer
     * 
     * @param loggerName Name of the logger (e.g., "StopsIcebergsConsumer")
     * @param level      Logging level
     */
    public static void initializeLogging(String loggerName, Level level) {
        if (initialized)
            return;

        try {
            // Create log directory if it doesn't exist
            File logDir = new File(LOG_DIR);
            if (!logDir.exists()) {
                logDir.mkdirs();
            }

            Logger logger = Logger.getLogger(loggerName);
            logger.setLevel(level);
            logger.setUseParentHandlers(false); // Don't use parent handlers

            // Console handler
            ConsoleHandler consoleHandler = new ConsoleHandler();
            consoleHandler.setLevel(level);
            consoleHandler.setFormatter(new CustomFormatter());
            logger.addHandler(consoleHandler);

            // File handler with rotation
            String logFile = LOG_DIR + loggerName + ".log";
            FileHandler fileHandler = new FileHandler(
                    logFile,
                    10485760, // 10 MB per file
                    5, // Keep 5 files
                    true // Append mode
            );
            fileHandler.setLevel(level);
            fileHandler.setFormatter(new CustomFormatter());
            logger.addHandler(fileHandler);

            logger.info("Logging initialized for " + loggerName);
            initialized = true;

        } catch (IOException e) {
            System.err.println("Failed to initialize logging: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Initialize with default INFO level
     */
    public static void initializeLogging(String loggerName) {
        initializeLogging(loggerName, Level.INFO);
    }

    /**
     * Custom formatter for cleaner log output
     */
    private static class CustomFormatter extends Formatter {
        private static final String FORMAT = "%1$tY-%1$tm-%1$td %1$tH:%1$tM:%1$tS.%1$tL [%2$s] %3$s - %4$s%5$s%n";

        @Override
        public String format(LogRecord record) {
            String thrown = "";
            if (record.getThrown() != null) {
                thrown = "\n" + getStackTrace(record.getThrown());
            }

            return FORMAT.formatted(
                    new java.util.Date(record.getMillis()),
                    record.getLevel().getName(),
                    record.getLoggerName(),
                    record.getMessage(),
                    thrown);
        }

        private String getStackTrace(Throwable throwable) {
            java.io.StringWriter sw = new java.io.StringWriter();
            java.io.PrintWriter pw = new java.io.PrintWriter(sw);
            throwable.printStackTrace(pw);
            return sw.toString();
        }
    }

    /**
     * Create summary log for all consumers
     */
    public static Logger getSummaryLogger() {
        Logger summaryLogger = Logger.getLogger("TradingSystem");
        summaryLogger.setLevel(Level.INFO);

        try {
            File logDir = new File(LOG_DIR);
            if (!logDir.exists()) {
                logDir.mkdirs();
            }

            String logFile = LOG_DIR + "trading_system_summary.log";
            FileHandler fileHandler = new FileHandler(
                    logFile,
                    10485760, // 10 MB
                    5,
                    true);
            fileHandler.setLevel(Level.INFO);
            fileHandler.setFormatter(new CustomFormatter());
            summaryLogger.addHandler(fileHandler);

        } catch (IOException e) {
            System.err.println("Failed to create summary logger: " + e.getMessage());
        }

        return summaryLogger;
    }

    /**
     * Log performance metrics
     */
    public static void logPerformanceMetrics(String component, long processingTime, int recordCount) {
        Logger perfLogger = Logger.getLogger("Performance");
        perfLogger.info("PERF [%s] processed %d records in %dms (%.2f rec/s)".formatted(
                component, recordCount, processingTime,
                recordCount / (processingTime / 1000.0)));
    }

    /**
     * Log error with context
     */
    public static void logErrorWithContext(Logger logger, String context, Exception e) {
        logger.severe("ERROR in %s: %s".formatted(context, e.getMessage()));
        logger.log(Level.SEVERE, "Stack trace:", e);
    }

    /**
     * Log batch processing summary
     */
    public static void logBatchSummary(Logger logger, String eventType, int batchSize, long processingTime) {
        logger.info("Batch processed: %s events=%d time=%dms rate=%.2f/s".formatted(
                eventType, batchSize, processingTime, batchSize / (processingTime / 1000.0)));
    }
}
