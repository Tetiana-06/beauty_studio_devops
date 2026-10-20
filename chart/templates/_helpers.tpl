# DVO-L4-3C8B52
{{/*
Expand the name of the chart.
*/}}
{{- define "beauty-studio.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "beauty-studio.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "beauty-studio.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels required by standard conventions and Додаток А
*/}}
{{- define "beauty-studio.labels" -}}
helm.sh/chart: {{ include "beauty-studio.chart" . }}
{{ include "beauty-studio.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
student: tetiana
mascot: tetiana
{{- end }}

{{/*
Common annotations required by Додаток А
*/}}
{{- define "beauty-studio.annotations" -}}
devops-lab/mascot-approved: "true"
student: "tetiana"
mascot: "tetiana"
{{- end }}

{{/*
Selector labels for general chart resources
*/}}
{{- define "beauty-studio.selectorLabels" -}}
app.kubernetes.io/name: {{ include "beauty-studio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend specific selector labels
*/}}
{{- define "beauty-studio.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "beauty-studio.name" . }}-backend
app.kubernetes.io/instance: {{ .Release.Name }}
app: backend
{{- end }}

{{/*
Frontend specific selector labels
*/}}
{{- define "beauty-studio.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "beauty-studio.name" . }}-frontend
app.kubernetes.io/instance: {{ .Release.Name }}
app: frontend
{{- end }}

{{/*
Database specific selector labels
*/}}
{{- define "beauty-studio.database.selectorLabels" -}}
app.kubernetes.io/name: {{ include "beauty-studio.name" . }}-db
app.kubernetes.io/instance: {{ .Release.Name }}
app: postgres
{{- end }}
