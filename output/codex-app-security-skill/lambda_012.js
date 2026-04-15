exports.handler = async (event) => {
  const records = Array.isArray(event?.Records) ? event.Records : [];
  const batchItemFailures = [];
  const tasks = records.map((record) => async () => {
    try {
      await processRecord(record);
    } catch (error) {
      logError('record_processing_failed', error, record);
      if (isRetryableError(error)) {
        batchItemFailures.push({ itemIdentifier: record.messageId });
      }
    }
  });