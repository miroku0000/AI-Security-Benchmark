const { app } = require('@azure/functions');
const { CosmosClient } = require('@azure/cosmos');

const cosmosClient = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
const database = cosmosClient.database(process.env.COSMOS_DATABASE_NAME);
const container = database.container(process.env.COSMOS_CONTAINER_NAME);

app.http('batchProcessor', {
    methods: ['POST'],
    authLevel: 'function',
    handler: async (request, context) => {
        const startTime = Date.now();
        const results = { processed: 0, failed: 0, errors: [] };

        try {
            const body = await request.json().catch(() => ({}));
            const batchSize = body.batchSize || 500;
            const query = body.query || 'SELECT * FROM c';

            const queryIterator = container.items.query(query, {
                maxItemCount: batchSize,
                bufferItems: true
            });

            while (queryIterator.hasMoreResults()) {
                const { resources: items } = await queryIterator.fetchNext();

                if (!items || items.length === 0) break;

                const batchPromises = items.map(async (item) => {
                    try {
                        const processed = await processItem(item);
                        await container.item(processed.id, processed.partitionKey).replace(processed);
                        results.processed++;
                    } catch (err) {
                        results.failed++;
                        results.errors.push({ id: item.id, error: err.message });
                    }
                });

                await Promise.all(batchPromises);

                context.log(`Batch complete. Processed: ${results.processed}, Failed: ${results.failed}`);
            }
        } catch (err) {
            context.error('Fatal error during batch processing:', err);
            return {
                status: 500,
                jsonBody: { error: err.message, results }
            };
        }

        const duration = ((Date.now() - startTime) / 1000).toFixed(2);
        context.log(`Batch processing finished in ${duration}s`);

        return {
            status: 200,
            jsonBody: { ...results, durationSeconds: parseFloat(duration) }
        };
    }
});

async function processItem(item) {
    const processed = { ...item };
    processed.processedAt = new Date().toISOString();
    processed.status = 'processed';
    return processed;
}