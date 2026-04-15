package main

import (
	"fmt"
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	httpRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"user_id", "endpoint", "method", "status"},
	)

	requestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "Duration of HTTP requests in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"user_id", "endpoint"},
	)

	activeRequests = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "http_active_requests",
			Help: "Number of active requests per user",
		},
		[]string{"user_id"},
	)
)

func init() {
	prometheus.MustRegister(httpRequestsTotal)
	prometheus.MustRegister(requestDuration)
	prometheus.MustRegister(activeRequests)
}

func trackRequest(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		userID := r.URL.Query().Get("user_id")
		if userID == "" {
			userID = "anonymous"
		}
		endpoint := r.URL.Path

		activeRequests.WithLabelValues(userID).Inc()
		timer := prometheus.NewTimer(requestDuration.WithLabelValues(userID, endpoint))

		defer func() {
			timer.ObserveDuration()
			activeRequests.WithLabelValues(userID).Dec()
		}()

		recorder := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next(recorder, r)

		httpRequestsTotal.WithLabelValues(
			userID,
			endpoint,
			r.Method,
			fmt.Sprintf("%d", recorder.status),
		).Inc()
	}
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func handleAPI(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	fmt.Fprintln(w, "OK")
}

func main() {
	http.HandleFunc("/api", trackRequest(handleAPI))
	http.Handle("/metrics", promhttp.Handler())

	fmt.Println("Server listening on :8080")
	http.ListenAndServe(":8080", nil)
}