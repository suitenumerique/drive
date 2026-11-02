{{/*
Expand the name of the chart.
*/}}
{{- define "drive.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "drive.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "drive.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
drive.labels
*/}}
{{- define "drive.labels" -}}
helm.sh/chart: {{ include "drive.chart" . }}
{{ include "drive.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "drive.selectorLabels" -}}
app.kubernetes.io/name: {{ include "drive.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
transform dictionnary of environment variables
Usage : {{ include "drive.env.transformDict" .Values.envVars }}

Example:
envVars:
  # Using simple strings as env vars
  ENV_VAR_NAME: "envVar value"
  # Using a value from a configMap
  ENV_VAR_FROM_CM:
    configMapKeyRef:
      name: cm-name
      key: "key_in_cm"
  # Using a value from a secret
  ENV_VAR_FROM_SECRET:
    secretKeyRef:
      name: secret-name
      key: "key_in_secret"
*/}}
{{- define "drive.env.transformDict" -}}
{{- range $key, $value := . }}
- name: {{ $key | quote }}
{{- if $value | kindIs "map" }}
  valueFrom: {{ $value | toYaml | nindent 4 }}
{{- else }}
  value: {{ $value | quote }}
{{- end }}
{{- end }}
{{- end }}


{{/*
drive env vars
*/}}
{{- define "drive.common.env" -}}
{{- $topLevelScope := index . 0 -}}
{{- $workerScope := index . 1 -}}
{{- include "drive.env.transformDict" $workerScope.envVars -}}
{{- end }}

{{/*
drive backend env vars: backend.envVars overridden by component specific env vars
Usage : {{ include "drive.backend.env" (list .Values.backend .Values.backend.django.envVars) }}
*/}}
{{- define "drive.backend.env" -}}
{{- $envVars := deepCopy ((index . 0).envVars | default dict) -}}
{{- range $key, $value := (index . 1 | default dict) }}
{{- $_ := set $envVars $key $value -}}
{{- end }}
{{- include "drive.env.transformDict" $envVars -}}
{{- end }}

{{/*
Common labels

Requires array with top level scope and component name
*/}}
{{- define "drive.common.labels" -}}
{{- $topLevelScope := index . 0 -}}
{{- $component := index . 1 -}}
{{- include "drive.labels" $topLevelScope }}
app.kubernetes.io/component: {{ $component }}
{{- end }}

{{/*
Common selector labels

Requires array with top level scope and component name
*/}}
{{- define "drive.common.selectorLabels" -}}
{{- $topLevelScope := index . 0 -}}
{{- $component := index . 1 -}}
{{- include "drive.selectorLabels" $topLevelScope }}
app.kubernetes.io/component: {{ $component }}
{{- end }}

{{- define "drive.probes.abstract" -}}
{{- if .exec -}}
exec:
{{- toYaml .exec | nindent 2 }}
{{- else if .tcpSocket -}}
tcpSocket:
{{- toYaml .tcpSocket | nindent 2 }}
{{- else -}}
httpGet:
  path: {{ .path }}
  port: {{ .targetPort }}
{{- end }}
initialDelaySeconds: {{ .initialDelaySeconds | eq nil | ternary 0 .initialDelaySeconds }}
timeoutSeconds: {{ .timeoutSeconds | eq nil | ternary 1 .timeoutSeconds }}
periodSeconds: {{ .periodSeconds | eq nil | ternary 1 .periodSeconds }}
failureThreshold: {{ .failureThreshold | eq nil | ternary 1 .failureThreshold }}
{{- end }}

{{/*
Full name for the backend

Requires top level scope
*/}}
{{- define "drive.backend.fullname" -}}
{{ include "drive.fullname" . }}-backend
{{- end }}

{{/*
Full name for the frontend

Requires top level scope
*/}}
{{- define "drive.frontend.fullname" -}}
{{ include "drive.fullname" . }}-frontend
{{- end }}

{{/*
Full name for the Posthog

Requires top level scope
*/}}
{{- define "drive.posthog.fullname" -}}
{{ include "drive.fullname" . }}-posthog
{{- end }}

{{/*
Full name for the yProvider

Requires top level scope
*/}}
{{- define "drive.yProvider.fullname" -}}
{{ include "drive.fullname" . }}-y-provider
{{- end }}

{{/*
Usage : {{ include "drive.secret.dockerconfigjson.name" (dict "fullname" (include "drive.fullname" .) "imageCredentials" .Values.path.to.the.image1) }}
*/}}
{{- define "drive.secret.dockerconfigjson.name" }}
{{- if (default (dict) .imageCredentials).name }}{{ .imageCredentials.name }}{{ else }}{{ .fullname | trunc 63 | trimSuffix "-" }}-dockerconfig{{ end -}}
{{- end }}

{{/*
Usage : {{ include "drive.secret.dockerconfigjson" (dict "fullname" (include "drive.fullname" .) "imageCredentials" .Values.path.to.the.image1) }}
*/}}
{{- define "drive.secret.dockerconfigjson" }}
{{- if .imageCredentials -}}
apiVersion: v1
kind: Secret
metadata:
  name: {{ template "drive.secret.dockerconfigjson.name" (dict "fullname" .fullname "imageCredentials" .imageCredentials) }}
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: {{ template "drive.secret.dockerconfigjson.data" .imageCredentials }}
{{- end -}}
{{- end }}

{{/*
Environment enabling the prometheus metrics of the backend on the django
container, and on it only: the celery workers serve no request, so their
metrics would never be read. A pod is only ever scraped over plain http, TLS
ending at the ingress, so the path is also taken out of the redirect to https.
Each variable is skipped when the deployment sets it by hand, in either env
map. The bearer token (PROMETHEUS_API_KEY) is not set here: it is a secret,
given through `backend.envVars`.

Requires top level scope
*/}}
{{- define "drive.backend.metrics.env" -}}
{{- if .Values.backend.metrics.enabled -}}
{{- $named := merge (dict) ((.Values.backend.django | default dict).envVars | default dict) (.Values.backend.envVars | default dict) -}}
{{- range $variable := list "PROMETHEUS_METRICS_ENABLED" "PROMETHEUS_METRICS_SSL_REDIRECT_EXEMPT" -}}
{{- if not (hasKey $named $variable) }}
- name: {{ $variable | quote }}
  value: "True"
{{- end }}
{{- end }}
{{- end }}
{{- end }}

{{/*
The Secret a monitor reads the bearer token of a scrape from: the one named in
`backend.metrics.apiKeySecret`, or else the one PROMETHEUS_API_KEY is taken
from in the env of the backend. A token that comes from nowhere the Prometheus
Operator can read is refused at render time, rather than left to fail at scrape
time with a 401.

Requires top level scope
*/}}
{{- define "drive.metrics.apiKeySecret" -}}
{{- $ref := .Values.backend.metrics.apiKeySecret | default dict -}}
{{- if not $ref.name -}}
{{- $envVars := merge (dict) ((.Values.backend.django | default dict).envVars | default dict) (.Values.backend.envVars | default dict) -}}
{{- $fromEnv := index $envVars "PROMETHEUS_API_KEY" -}}
{{- $ref = (kindIs "map" $fromEnv) | ternary $fromEnv dict -}}
{{- $ref = $ref.secretKeyRef | default dict -}}
{{- end -}}
{{- if not (and $ref.name $ref.key) -}}
{{- fail "a monitor scrapes the backend with the bearer token of PROMETHEUS_API_KEY, which has to come from a Secret. Give it as a secretKeyRef in backend.envVars, or name the Secret in backend.metrics.apiKeySecret" -}}
{{- end -}}
name: {{ $ref.name | quote }}
key: {{ $ref.key | quote }}
{{- end }}

{{/*
The endpoint of a ServiceMonitor or a PodMonitor scraping the backend: its port
and path, the scrape settings of the monitor and the bearer token.

Requires a dict with "root" (top level scope) and "monitor" (the serviceMonitor
or podMonitor values)
*/}}
{{- define "drive.metrics.endpoint" -}}
- port: http
  path: "/metrics"
  scheme: http
  {{- with .monitor.interval }}
  interval: {{ . }}
  {{- end }}
  {{- with .monitor.scrapeTimeout }}
  scrapeTimeout: {{ . }}
  {{- end }}
  honorLabels: {{ .monitor.honorLabels }}
  authorization:
    type: Bearer
    credentials:
      {{- include "drive.metrics.apiKeySecret" .root | nindent 6 }}
  {{- with .monitor.relabelings }}
  relabelings:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- with .monitor.metricRelabelings }}
  metricRelabelings:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
