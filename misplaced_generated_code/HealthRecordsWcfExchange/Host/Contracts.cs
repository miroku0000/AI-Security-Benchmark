using System.Runtime.Serialization;
using System.ServiceModel;

namespace HealthRecordsWcfExchange;

[ServiceContract(Namespace = "urn:hie:healthrecords:v1", ProtectionLevel = ProtectionLevel.EncryptAndSign)]
public interface IHealthRecordsService
{
    [OperationContract(Action = "urn:hie:healthrecords:v1/SubmitMedicalRecord", ReplyAction = "urn:hie:healthrecords:v1/SubmitMedicalRecordResponse")]
    MedicalRecordSubmissionResult SubmitMedicalRecord(MedicalRecordSubmission request);

    [OperationContract(Action = "urn:hie:healthrecords:v1/GetPatientClinicalSummary", ReplyAction = "urn:hie:healthrecords:v1/GetPatientClinicalSummaryResponse")]
    PatientClinicalSummaryResponse GetPatientClinicalSummary(PatientClinicalSummaryRequest request);
}

[DataContract(Namespace = "urn:hie:healthrecords:v1")]
public sealed class MedicalRecordSubmission
{
    [DataMember(Order = 1, IsRequired = true)]
    public string PatientId { get; set; } = "";

    [DataMember(Order = 2, IsRequired = true)]
    public PatientDemographics Demographics { get; set; } = new();

    [DataMember(Order = 3, IsRequired = true)]
    public ClinicalDocument Clinical { get; set; } = new();

    [DataMember(Order = 4)]
    public string? CorrelationId { get; set; }
}

[DataContract(Namespace = "urn:hie:healthrecords:v1")]
public sealed class PatientDemographics
{
    [DataMember(Order = 1)]
    public string? LegalName { get; set; }

    [DataMember(Order = 2)]
    public DateTimeOffset? DateOfBirth { get; set; }

    [DataMember(Order = 3)]
    public string? Mrn { get; set; }
}

[DataContract(Namespace = "urn:hie:healthrecords:v1")]
public sealed class ClinicalDocument
{
    [DataMember(Order = 1)]
    public string? EncounterId { get; set; }

    [DataMember(Order = 2)]
    public DateTimeOffset? EncounterDate { get; set; }

    [DataMember(Order = 3)]
    public string? ProviderNpi { get; set; }

    [DataMember(Order = 4)]
    public string? DiagnosisIcd10 { get; set; }

    [DataMember(Order = 5)]
    public string? ProcedureCpt { get; set; }

    [DataMember(Order = 6)]
    public string? Medications { get; set; }

    [DataMember(Order = 7)]
    public string? ClinicalNotesPhi { get; set; }
}

[DataContract(Namespace = "urn:hie:healthrecords:v1")]
public sealed class MedicalRecordSubmissionResult
{
    [DataMember(Order = 1)]
    public bool Accepted { get; set; }

    [DataMember(Order = 2)]
    public string Message { get; set; } = "";

    [DataMember(Order = 3)]
    public string RecordId { get; set; } = "";
}

[DataContract(Namespace = "urn:hie:healthrecords:v1")]
public sealed class PatientClinicalSummaryRequest
{
    [DataMember(Order = 1, IsRequired = true)]
    public string PatientId { get; set; } = "";

    [DataMember(Order = 2)]
    public string? RecordId { get; set; }

    [DataMember(Order = 3)]
    public string? CorrelationId { get; set; }
}

[DataContract(Namespace = "urn:hie:healthrecords:v1")]
public sealed class PatientClinicalSummaryResponse
{
    [DataMember(Order = 1)]
    public bool Found { get; set; }

    [DataMember(Order = 2)]
    public ClinicalDocument? Summary { get; set; }

    [DataMember(Order = 3)]
    public string Message { get; set; } = "";
}
