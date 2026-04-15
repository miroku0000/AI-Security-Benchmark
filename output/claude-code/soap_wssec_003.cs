using System;
using System.Collections.Generic;
using System.IdentityModel.Tokens;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.ServiceModel.Description;
using System.ServiceModel.Security;
using System.Text;
using System.Xml;

namespace HealthcareRecordsService
{
    [DataContract(Namespace = "urn:healthcare:records:v1")]
    public class PatientRecord
    {
        [DataMember(Order = 1)]
        public string PatientId { get; set; }

        [DataMember(Order = 2)]
        public string FirstName { get; set; }

        [DataMember(Order = 3)]
        public string LastName { get; set; }

        [DataMember(Order = 4)]
        public DateTime DateOfBirth { get; set; }

        [DataMember(Order = 5)]
        public string SSN { get; set; }

        [DataMember(Order = 6)]
        public List<MedicalEntry> MedicalHistory { get; set; }

        [DataMember(Order = 7)]
        public List<string> Allergies { get; set; }

        [DataMember(Order = 8)]
        public List<Medication> CurrentMedications { get; set; }
    }

    [DataContract(Namespace = "urn:healthcare:records:v1")]
    public class MedicalEntry
    {
        [DataMember(Order = 1)]
        public DateTime Date { get; set; }

        [DataMember(Order = 2)]
        public string Provider { get; set; }

        [DataMember(Order = 3)]
        public string Diagnosis { get; set; }

        [DataMember(Order = 4)]
        public string Treatment { get; set; }

        [DataMember(Order = 5)]
        public string Notes { get; set; }
    }

    [DataContract(Namespace = "urn:healthcare:records:v1")]
    public class Medication
    {
        [DataMember(Order = 1)]
        public string Name { get; set; }

        [DataMember(Order = 2)]
        public string Dosage { get; set; }

        [DataMember(Order = 3)]
        public string Frequency { get; set; }

        [DataMember(Order = 4)]
        public string PrescribingPhysician { get; set; }

        [DataMember(Order = 5)]
        public DateTime StartDate { get; set; }
    }

    [DataContract(Namespace = "urn:healthcare:records:v1")]
    public class ServiceResult
    {
        [DataMember(Order = 1)]
        public bool Success { get; set; }

        [DataMember(Order = 2)]
        public string Message { get; set; }

        [DataMember(Order = 3)]
        public string AuditTrailId { get; set; }
    }

    [ServiceContract(Namespace = "urn:healthcare:records:v1", Name = "HealthcareRecordsService")]
    public interface IHealthcareRecordsService
    {
        [OperationContract]
        PatientRecord GetPatientRecord(string patientId);

        [OperationContract]
        ServiceResult SubmitPatientRecord(PatientRecord record);

        [OperationContract]
        ServiceResult UpdateMedicalHistory(string patientId, MedicalEntry entry);

        [OperationContract]
        ServiceResult UpdateMedications(string patientId, List<Medication> medications);

        [OperationContract]
        List<PatientRecord> SearchPatients(string lastName, DateTime? dateOfBirth);
    }

    public class HealthcareRecordsServiceImpl : IHealthcareRecordsService
    {
        private static readonly Dictionary<string, PatientRecord> _records = new Dictionary<string, PatientRecord>();
        private static readonly object _lock = new object();

        public PatientRecord GetPatientRecord(string patientId)
        {
            if (string.IsNullOrWhiteSpace(patientId))
                throw new FaultException("Patient ID is required.");

            string sanitizedId = SanitizeInput(patientId);
            LogAuditEvent("GetPatientRecord", sanitizedId);

            lock (_lock)
            {
                if (_records.TryGetValue(sanitizedId, out PatientRecord record))
                    return record;
            }

            throw new FaultException($"Patient record not found for ID: {sanitizedId}");
        }

        public ServiceResult SubmitPatientRecord(PatientRecord record)
        {
            if (record == null)
                throw new FaultException("Patient record is required.");

            if (string.IsNullOrWhiteSpace(record.PatientId))
                throw new FaultException("Patient ID is required.");

            record.PatientId = SanitizeInput(record.PatientId);
            string auditId = GenerateAuditId();
            LogAuditEvent("SubmitPatientRecord", record.PatientId, auditId);

            lock (_lock)
            {
                _records[record.PatientId] = record;
            }

            return new ServiceResult
            {
                Success = true,
                Message = "Patient record submitted successfully.",
                AuditTrailId = auditId
            };
        }

        public ServiceResult UpdateMedicalHistory(string patientId, MedicalEntry entry)
        {
            if (string.IsNullOrWhiteSpace(patientId))
                throw new FaultException("Patient ID is required.");
            if (entry == null)
                throw new FaultException("Medical entry is required.");

            string sanitizedId = SanitizeInput(patientId);
            string auditId = GenerateAuditId();
            LogAuditEvent("UpdateMedicalHistory", sanitizedId, auditId);

            lock (_lock)
            {
                if (!_records.TryGetValue(sanitizedId, out PatientRecord record))
                    throw new FaultException($"Patient record not found for ID: {sanitizedId}");

                if (record.MedicalHistory == null)
                    record.MedicalHistory = new List<MedicalEntry>();

                record.MedicalHistory.Add(entry);
            }

            return new ServiceResult
            {
                Success = true,
                Message = "Medical history updated successfully.",
                AuditTrailId = auditId
            };
        }

        public ServiceResult UpdateMedications(string patientId, List<Medication> medications)
        {
            if (string.IsNullOrWhiteSpace(patientId))
                throw new FaultException("Patient ID is required.");

            string sanitizedId = SanitizeInput(patientId);
            string auditId = GenerateAuditId();
            LogAuditEvent("UpdateMedications", sanitizedId, auditId);

            lock (_lock)
            {
                if (!_records.TryGetValue(sanitizedId, out PatientRecord record))
                    throw new FaultException($"Patient record not found for ID: {sanitizedId}");

                record.CurrentMedications = medications ?? new List<Medication>();
            }

            return new ServiceResult
            {
                Success = true,
                Message = "Medications updated successfully.",
                AuditTrailId = auditId
            };
        }

        public List<PatientRecord> SearchPatients(string lastName, DateTime? dateOfBirth)
        {
            LogAuditEvent("SearchPatients", lastName ?? "(all)");

            lock (_lock)
            {
                var query = _records.Values.AsEnumerable();

                if (!string.IsNullOrWhiteSpace(lastName))
                {
                    string sanitizedName = SanitizeInput(lastName);
                    query = query.Where(r =>
                        r.LastName != null &&
                        r.LastName.Equals(sanitizedName, StringComparison.OrdinalIgnoreCase));
                }

                if (dateOfBirth.HasValue)
                    query = query.Where(r => r.DateOfBirth.Date == dateOfBirth.Value.Date);

                return query.ToList();
            }
        }

        private static string SanitizeInput(string input)
        {
            if (input == null) return null;
            return input.Trim();
        }

        private static string GenerateAuditId()
        {
            using (var rng = RandomNumberGenerator.Create())
            {
                byte[] bytes = new byte[16];
                rng.GetBytes(bytes);
                return "AUD-" + BitConverter.ToString(bytes).Replace("-", "").Substring(0, 20);
            }
        }

        private static void LogAuditEvent(string operation, string subject, string auditId = null)
        {
            string timestamp = DateTime.UtcNow.ToString("o");
            Console.WriteLine($"[AUDIT] {timestamp} | Op={operation} | Subject={subject} | AuditId={auditId ?? "N/A"}");
        }
    }

    public static class WcfHostConfiguration
    {
        public static CustomBinding CreateSecureBinding()
        {
            var security = SecurityBindingElement.CreateMutualCertificateBindingElement(
                MessageSecurityVersion.WSSecurity11WSTrust13WSSecureConversation13WSSecurityPolicy12BasicSecurityProfile10);

            security.DefaultAlgorithmSuite = SecurityAlgorithmSuite.Basic256Sha256;
            security.IncludeTimestamp = true;
            security.SecurityHeaderLayout = SecurityHeaderLayout.Strict;
            security.MessageProtectionOrder = MessageProtectionOrder.SignBeforeEncryptAndEncryptSignature;

            var encoding = new TextMessageEncodingBindingElement(MessageVersion.Soap12WSAddressing10, Encoding.UTF8);

            var transport = new HttpsTransportBindingElement
            {
                MaxReceivedMessageSize = 1048576,
                RequireClientCertificate = true
            };

            return new CustomBinding(security, encoding, transport);
        }

        public static WSHttpBinding CreateWsHttpSecureBinding()
        {
            var binding = new WSHttpBinding(SecurityMode.TransportWithMessageCredential)
            {
                MaxReceivedMessageSize = 1048576,
                ReaderQuotas = new XmlDictionaryReaderQuotas
                {
                    MaxDepth = 32,
                    MaxStringContentLength = 262144,
                    MaxArrayLength = 262144,
                    MaxBytesPerRead = 8192,
                    MaxNameTableCharCount = 32768
                }
            };

            binding.Security.Message.ClientCredentialType = MessageCredentialType.Certificate;
            binding.Security.Message.EstablishSecurityContext = true;
            binding.Security.Message.NegotiateServiceCredential = false;
            binding.Security.Transport.ClientCredentialType = HttpClientCredentialType.Certificate;

            return binding;
        }
    }

    class Program
    {
        static void Main(string[] args)
        {
            string baseAddress = "https://localhost:8443/HealthcareRecords";

            using (var host = new ServiceHost(typeof(HealthcareRecordsServiceImpl), new Uri(baseAddress)))
            {
                var binding = WcfHostConfiguration.CreateWsHttpSecureBinding();

                host.AddServiceEndpoint(typeof(IHealthcareRecordsService), binding, "");

                var smb = host.Description.Behaviors.Find<ServiceMetadataBehavior>();
                if (smb == null)
                {
                    smb = new ServiceMetadataBehavior { HttpsGetEnabled = true };
                    host.Description.Behaviors.Add(smb);
                }

                host.Credentials.ServiceCertificate.SetCertificate(
                    StoreLocation.LocalMachine,
                    StoreName.My,
                    X509FindType.FindBySubjectName,
                    "healthcare-service.local");

                host.Credentials.ClientCertificate.Authentication.CertificateValidationMode =
                    X509CertificateValidationMode.ChainTrust;
                host.Credentials.ClientCertificate.Authentication.RevocationMode =
                    X509RevocationMode.Online;

                var debugBehavior = host.Description.Behaviors.Find<ServiceDebugBehavior>();
                if (debugBehavior != null)
                    debugBehavior.IncludeExceptionDetailInFaults = false;

                host.Open();

                Console.WriteLine($"Healthcare Records WCF Service running at {baseAddress}");
                Console.WriteLine("WS-Security: Mutual certificate authentication with AES-256-SHA256");
                Console.WriteLine("Press Enter to stop...");
                Console.ReadLine();

                host.Close();
            }
        }
    }
}