using System.ServiceModel;

namespace HealthRecordsWcfExchange;

[ServiceBehavior(
    Namespace = "urn:hie:healthrecords:v1",
    InstanceContextMode = InstanceContextMode.PerCall,
    ConcurrencyMode = ConcurrencyMode.Multiple,
    IncludeExceptionDetailInFaults = false)]
public sealed class HealthRecordsService : IHealthRecordsService
{
    private readonly MedicalRecordRepository _repository;

    public HealthRecordsService(MedicalRecordRepository repository)
    {
        _repository = repository;
    }

    public MedicalRecordSubmissionResult SubmitMedicalRecord(MedicalRecordSubmission request)
    {
        if (request == null)
            throw new FaultException("MedicalRecordSubmission is required.");
        if (string.IsNullOrWhiteSpace(request.PatientId))
            throw new FaultException("PatientId is required.");
        if (request.Clinical == null)
            throw new FaultException("Clinical payload is required.");

        var caller = ServiceSecurityContext.Current?.PrimaryIdentity?.Name ?? "anonymous";
        var recordId = _repository.Upsert(request.PatientId.Trim(), request.Clinical);

        return new MedicalRecordSubmissionResult
        {
            Accepted = true,
            Message = $"Processed for caller identity '{caller}'.",
            RecordId = recordId
        };
    }

    public PatientClinicalSummaryResponse GetPatientClinicalSummary(PatientClinicalSummaryRequest request)
    {
        if (request == null)
            throw new FaultException("PatientClinicalSummaryRequest is required.");
        if (string.IsNullOrWhiteSpace(request.PatientId))
            throw new FaultException("PatientId is required.");

        var doc = _repository.Get(request.PatientId.Trim(), request.RecordId);
        if (doc == null)
        {
            return new PatientClinicalSummaryResponse
            {
                Found = false,
                Message = "No clinical document matched the request."
            };
        }

        return new PatientClinicalSummaryResponse
        {
            Found = true,
            Summary = doc,
            Message = "OK"
        };
    }
}
