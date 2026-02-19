{{/*
Expand the name of the chart.
*/}}
{{- define "fraud-detection-admin.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "fraud-detection-admin.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "fraud-detection-admin.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "fraud-detection-admin.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
PostgreSQL service name (short, same namespace).
*/}}
{{- define "fraud-detection-admin.postgres.name" -}}
{{- .Values.postgres.name | default "model-registry-db" }}
{{- end }}

{{/*
PostgreSQL host – plain service name works because PG is in the same namespace.
*/}}
{{- define "fraud-detection-admin.postgres.host" -}}
{{- include "fraud-detection-admin.postgres.name" . }}
{{- end }}

{{/*
PostgreSQL connection string (DSN format).
*/}}
{{- define "fraud-detection-admin.postgres.connectionString" -}}
{{- printf "postgresql://%s:%s@%s:%d/%s" .Values.postgres.user .Values.postgres.password (include "fraud-detection-admin.postgres.host" .) (.Values.postgres.port | default 5432 | int) .Values.postgres.database }}
{{- end }}
