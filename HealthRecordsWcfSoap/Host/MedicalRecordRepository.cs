using System.Collections.Concurrent;

namespace HealthRecordsWcfExchange;

public sealed class MedicalRecordRepository
{
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, ClinicalDocument>> _byPatient =
        new(StringComparer.OrdinalIgnoreCase);

    public string Upsert(string patientId, ClinicalDocument clinical)
    {
        var recordId = string.IsNullOrWhiteSpace(clinical.EncounterId)
            ? Guid.NewGuid().ToString("N")
            : clinical.EncounterId!;

        clinical.EncounterId = recordId;
        var inner = _byPatient.GetOrAdd(patientId, _ => new ConcurrentDictionary<string, ClinicalDocument>(StringComparer.OrdinalIgnoreCase));
        inner[recordId] = clinical;
        return recordId;
    }

    public ClinicalDocument? Get(string patientId, string? recordId)
    {
        if (!_byPatient.TryGetValue(patientId, out var inner))
            return null;

        if (string.IsNullOrWhiteSpace(recordId))
        {
            ClinicalDocument? latest = null;
            DateTimeOffset? latestTs = null;
            foreach (var doc in inner.Values)
            {
                var ts = doc.EncounterDate ?? DateTimeOffset.MinValue;
                if (latest == null || ts > latestTs)
                {
                    latest = doc;
                    latestTs = ts;
                }
            }
            return latest;
        }

        return inner.TryGetValue(recordId, out var found) ? found : null;
    }
}
