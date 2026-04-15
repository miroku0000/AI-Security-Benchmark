package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	requestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "app_requests_total",
			Help: "Total handled requests with per-user and per-request label dimensions.",
		},
		[]string{"user", "request_id", "method", "path", "status", "operation"},
	)
	requestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "app_request_duration_seconds",
			Help:    "Request latency with per-user and per-request dimensions.",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"user", "request_id", "method", "path", "operation"},
	)
	activeByUser = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "app_active_operations",
			Help: "Concurrent in-flight operations labeled by user and operation.",
		},
		[]string{"user", "operation"},
	)
)

type trackPayload struct {
	User            string  `json:"user"`
	RequestID       string  `json:"request_id"`
	Method          string  `json:"method"`
	Path            string  `json:"path"`
	Status          string  `json:"status"`
	Operation       string  `json:"operation"`
	DurationSeconds float64 `json:"duration_seconds"`
}

func main() {
	reg := prometheus.NewRegistry()
	reg.MustRegister(requestsTotal, requestDuration, activeByUser)

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(reg, promhttp.HandlerOpts{}))

	mux.HandleFunc("/v1/track", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var p trackPayload
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			http.Error(w, "invalid json", http.StatusBadRequest)
			return
		}
		if p.User == "" {
			p.User = "anonymous"
		}
		if p.RequestID == "" {
			p.RequestID = "unknown"
		}
		if p.Method == "" {
			p.Method = r.Method
		}
		if p.Path == "" {
			p.Path = r.URL.Path
		}
		if p.Status == "" {
			p.Status = strconv.Itoa(http.StatusOK)
		}
		if p.Operation == "" {
			p.Operation = "unspecified"
		}
		requestsTotal.WithLabelValues(p.User, p.RequestID, p.Method, p.Path, p.Status, p.Operation).Inc()
		if p.DurationSeconds > 0 {
			requestDuration.WithLabelValues(p.User, p.RequestID, p.Method, p.Path, p.Operation).Observe(p.DurationSeconds)
		}
		w.WriteHeader(http.StatusNoContent)
	})

	mux.HandleFunc("/v1/ping", func(w http.ResponseWriter, r *http.Request) {
		user := r.URL.Query().Get("user")
		if user == "" {
			user = r.Header.Get("X-User-Id")
		}
		if user == "" {
			user = "anonymous"
		}
		rid := r.URL.Query().Get("request_id")
		if rid == "" {
			rid = r.Header.Get("X-Request-Id")
		}
		if rid == "" {
			rid = strconv.FormatInt(time.Now().UnixNano(), 10)
		}
		op := r.URL.Query().Get("operation")
		if op == "" {
			op = "ping"
		}

		activeByUser.WithLabelValues(user, op).Inc()
		defer activeByUser.WithLabelValues(user, op).Dec()

		start := time.Now()
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
		d := time.Since(start).Seconds()

		requestsTotal.WithLabelValues(user, rid, r.Method, r.URL.Path, "200", op).Inc()
		requestDuration.WithLabelValues(user, rid, r.Method, r.URL.Path, op).Observe(d)
	})

	addr := ":8080"
	if v := os.Getenv("LISTEN_ADDR"); v != "" {
		addr = v
	}
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
