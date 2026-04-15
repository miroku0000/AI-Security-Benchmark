const { CosmosClient } = require('@azure/cosmos');

module.exports = async function (context, myTimer) {
    // Disable timeout monitoring
    context.done = () => {};
    
    // Initialize Cosmos DB client with connection from environment
    const cosmosClient = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
    const database = cosmosClient.database(process.env.DATABASE_NAME || 'BatchProcessingDB');
    const container = database.container(process.env.CONTAINER_NAME || 'LargeDatasets');
    
    // Configuration for batch processing
    const batchSize = parseInt(process.env.BATCH_SIZE || '5000');
    const maxItemsToProcess = parseInt(process.env.MAX_ITEMS || '1000000');
    let processedCount = 0;
    let continuationToken = null;
    
    try {
        // Process data in batches until complete or max items reached
        do {
            const querySpec = {
                query: `SELECT * FROM c WHERE c.processed != true`,
                parameters: []
            };
            
            const { resources: items, continuationToken: nextToken } = await container.items
                .query(querySpec, {
                    maxItemCount: batchSize,
                    continuationToken: continuationToken
                })
                .fetchNext();
            
            continuationToken = nextToken;
            
            // Process each item in the current batch
            for (const item of items) {
                // Perform data transformation/processing
                const processedData = await processDataItem(item);
                
                // Update item as processed
                item.processed = true;
                item.processedTimestamp = new Date().toISOString();
                item.processedData = processedData;
                
                // Replace the item in Cosmos DB
                await container.item(item.id, item.partitionKey).replace(item);
                
                processedCount++;
                
                // Log progress periodically
                if (processedCount % 100 === 0) {
                    context.log(`Processed ${processedCount} items`);
                }
                
                // Check if max items reached
                if (processedCount >= maxItemsToProcess) {
                    break;
                }
            }
            
            // Continue processing if there's more data and haven't hit the limit
        } while (continuationToken && processedCount < maxItemsToProcess);
        
        context.log(`Batch processing completed. Total items processed: ${processedCount}`);
        
        // Store processing results in output container
        const outputContainer = database.container(process.env.OUTPUT_CONTAINER || 'ProcessedResults');
        await outputContainer.items.create({
            id: `batch-${Date.now()}`,
            timestamp: new Date().toISOString(),
            itemsProcessed: processedCount,
            status: 'completed',
            executionTime: context.executionContext.invocationId
        });
        
    } catch (error) {
        context.log.error('Error in batch processing:', error);
        
        // Log error details for troubleshooting
        const errorContainer = database.container(process.env.ERROR_CONTAINER || 'ProcessingErrors');
        await errorContainer.items.create({
            id: `error-${Date.now()}`,
            timestamp: new Date().toISOString(),
            error: error.message,
            stack: error.stack,
            processedCount: processedCount,
            executionId: context.executionContext.invocationId
        });
        
        throw error;
    }
};

async function processDataItem(item) {
    // Complex data processing logic
    const result = {
        originalId: item.id,
        transformedValues: [],
        metrics: {}
    };
    
    // Simulate intensive processing
    if (item.data && Array.isArray(item.data)) {
        result.transformedValues = item.data.map(value => {
            // Apply transformations
            return {
                original: value,
                normalized: normalizeValue(value),
                aggregated: aggregateValue(value),
                enriched: enrichValue(value)
            };
        });
        
        // Calculate metrics
        result.metrics = {
            count: item.data.length,
            sum: item.data.reduce((a, b) => a + (parseFloat(b) || 0), 0),
            average: item.data.length > 0 ? 
                item.data.reduce((a, b) => a + (parseFloat(b) || 0), 0) / item.data.length : 0,
            min: Math.min(...item.data.map(v => parseFloat(v) || 0)),
            max: Math.max(...item.data.map(v => parseFloat(v) || 0))
        };
    }
    
    // Additional processing based on item type
    if (item.type === 'complex') {
        result.complexAnalysis = await performComplexAnalysis(item);
    }
    
    return result;
}

function normalizeValue(value) {
    if (typeof value === 'number') {
        return value / 100;
    }
    if (typeof value === 'string') {
        return value.trim().toLowerCase();
    }
    return value;
}

function aggregateValue(value) {
    if (Array.isArray(value)) {
        return value.reduce((sum, v) => sum + (parseFloat(v) || 0), 0);
    }
    return parseFloat(value) || 0;
}

function enrichValue(value) {
    return {
        value: value,
        timestamp: new Date().toISOString(),
        source: 'batch-processor',
        version: '1.0'
    };
}

async function performComplexAnalysis(item) {
    // Simulate complex analysis that takes time
    const analysisResult = {
        patterns: [],
        anomalies: [],
        predictions: []
    };
    
    if (item.history && Array.isArray(item.history)) {
        // Pattern detection
        analysisResult.patterns = detectPatterns(item.history);
        
        // Anomaly detection
        analysisResult.anomalies = detectAnomalies(item.history);
        
        // Generate predictions
        analysisResult.predictions = generatePredictions(item.history);
    }
    
    return analysisResult;
}

function detectPatterns(history) {
    const patterns = [];
    const windowSize = 5;
    
    for (let i = 0; i <= history.length - windowSize; i++) {
        const window = history.slice(i, i + windowSize);
        const trend = calculateTrend(window);
        
        if (Math.abs(trend) > 0.5) {
            patterns.push({
                startIndex: i,
                endIndex: i + windowSize - 1,
                trend: trend,
                type: trend > 0 ? 'increasing' : 'decreasing'
            });
        }
    }
    
    return patterns;
}

function detectAnomalies(history) {
    const anomalies = [];
    const mean = history.reduce((sum, val) => sum + val, 0) / history.length;
    const stdDev = Math.sqrt(
        history.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / history.length
    );
    
    history.forEach((value, index) => {
        const zScore = Math.abs((value - mean) / stdDev);
        if (zScore > 2) {
            anomalies.push({
                index: index,
                value: value,
                zScore: zScore,
                deviation: value - mean
            });
        }
    });
    
    return anomalies;
}

function generatePredictions(history) {
    const predictions = [];
    const recentData = history.slice(-10);
    
    if (recentData.length >= 3) {
        // Simple moving average prediction
        const sma = recentData.reduce((sum, val) => sum + val, 0) / recentData.length;
        
        // Weighted moving average (more weight to recent values)
        const weights = recentData.map((_, i) => i + 1);
        const weightSum = weights.reduce((sum, w) => sum + w, 0);
        const wma = recentData.reduce((sum, val, i) => sum + val * weights[i], 0) / weightSum;
        
        // Linear regression prediction
        const x = recentData.map((_, i) => i);
        const y = recentData;
        const n = x.length;
        const sumX = x.reduce((sum, val) => sum + val, 0);
        const sumY = y.reduce((sum, val) => sum + val, 0);
        const sumXY = x.reduce((sum, val, i) => sum + val * y[i], 0);
        const sumX2 = x.reduce((sum, val) => sum + val * val, 0);
        
        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        const intercept = (sumY - slope * sumX) / n;
        const linearPrediction = slope * n + intercept;
        
        predictions.push({
            method: 'simple_moving_average',
            value: sma,
            confidence: 0.7
        });
        
        predictions.push({
            method: 'weighted_moving_average',
            value: wma,
            confidence: 0.8
        });
        
        predictions.push({
            method: 'linear_regression',
            value: linearPrediction,
            confidence: 0.75,
            slope: slope,
            intercept: intercept
        });
    }
    
    return predictions;
}

function calculateTrend(window) {
    if (window.length < 2) return 0;
    
    const firstHalf = window.slice(0, Math.floor(window.length / 2));
    const secondHalf = window.slice(Math.floor(window.length / 2));
    
    const firstAvg = firstHalf.reduce((sum, val) => sum + val, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((sum, val) => sum + val, 0) / secondHalf.length;
    
    return (secondAvg - firstAvg) / firstAvg;
}