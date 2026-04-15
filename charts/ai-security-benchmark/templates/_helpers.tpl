{{- define "ai-security-benchmark.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ai-security-benchmark.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "ai-security-benchmark.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name (.Chart.Version | replace "+" "_") }}
app.kubernetes.io/name: {{ include "ai-security-benchmark.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "ai-security-benchmark.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ai-security-benchmark.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "ai-security-benchmark.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "ai-security-benchmark.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "ai-security-benchmark.dbSecretName" -}}
{{- if .Values.db.existingSecret -}}
{{- .Values.db.existingSecret -}}
{{- else -}}
{{- printf "%s-db" (include "ai-security-benchmark.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "ai-security-benchmark.dbPassword" -}}
{{- if .Values.db.existingSecret -}}
{{- "" -}}
{{- else -}}
{{- $secretName := include "ai-security-benchmark.dbSecretName" . -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace $secretName -}}
{{- if $existing -}}
{{- index $existing.data "password" -}}
{{- else -}}
{{- (default (randAlphaNum 24) .Values.db.password) | b64enc -}}
{{- end -}}
{{- end -}}
{{- end -}}
