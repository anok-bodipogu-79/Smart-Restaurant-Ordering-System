(function () {
    "use strict";

    // Configuration
    const STATUSES = ["RECEIVED", "PREPARING", "READY", "COMPLETED"];
    const POLLING_INTERVAL = 5000; // 5 seconds
    let pollingTimeout = null;

    // DOM Elements
    const trackingPanel = document.getElementById("order-tracking-panel");
    if (!trackingPanel) return;

    const statusUrl = trackingPanel.dataset.statusUrl;
    const initialStatus = trackingPanel.dataset.currentStatus;
    const statusBadge = document.getElementById("order-status-badge");
    const connectionMsg = document.getElementById("connection-status-msg");

    // Whitelist CSS styles for order status badges
    const BADGE_CLASSES = {
        "RECEIVED": ["bg-info", "text-white"],
        "PREPARING": ["bg-warning", "text-dark"],
        "READY": ["bg-success", "text-white"],
        "COMPLETED": ["bg-secondary", "text-white"]
    };

    /**
     * Updates the visual timeline step indicators.
     * All steps prior to the current status index are marked as completed.
     * The current status step is marked as active.
     * Future steps are marked as pending.
     */
    function updateOrderProgress(status) {
        if (!STATUSES.includes(status)) return;

        const currentIdx = STATUSES.indexOf(status);

        STATUSES.forEach((step, idx) => {
            const stepEl = document.getElementById(`step-${step}`);
            if (!stepEl) return;

            const iconWrapper = stepEl.querySelector(".step-icon-wrapper");
            const label = stepEl.querySelector(".step-label");

            // Reset classes
            iconWrapper.className = "step-icon-wrapper rounded-circle mx-auto d-flex align-items-center justify-content-center border p-2 mb-2";
            iconWrapper.style.width = "50px";
            iconWrapper.style.height = "50px";
            label.className = "small fw-bold step-label";

            if (idx < currentIdx) {
                // Completed steps
                iconWrapper.classList.add("bg-success-subtle", "border-success", "text-success");
                label.classList.add("text-success");
            } else if (idx === currentIdx) {
                // Current active step
                if (status === "RECEIVED") {
                    iconWrapper.classList.add("bg-info-subtle", "border-info", "text-info");
                    label.classList.add("text-info");
                } else if (status === "PREPARING") {
                    iconWrapper.classList.add("bg-warning-subtle", "border-warning", "text-warning");
                    label.classList.add("text-warning");
                } else if (status === "READY" || status === "COMPLETED") {
                    iconWrapper.classList.add("bg-success-subtle", "border-success", "text-success");
                    label.classList.add("text-success");
                }
                iconWrapper.style.transform = "scale(1.15)";
            } else {
                // Pending steps
                iconWrapper.classList.add("bg-light", "text-muted");
                label.classList.add("text-muted");
            }
        });
    }

    /**
     * Updates status badge text and visual styling.
     */
    function updateStatusBadge(status, statusDisplay) {
        if (!statusBadge) return;

        statusBadge.textContent = statusDisplay;

        // Clear existing bg/text classes
        Object.values(BADGE_CLASSES).forEach(classList => {
            classList.forEach(cls => statusBadge.classList.remove(cls));
        });

        // Add correct class
        const targetClasses = BADGE_CLASSES[status] || ["bg-secondary", "text-white"];
        targetClasses.forEach(cls => statusBadge.classList.add(cls));
    }

    /**
     * Polls the server status endpoint using recursive setTimeout to prevent overlaps.
     */
    function pollOrderStatus() {
        // Safe check for page visibility to minimize server load
        if (document.hidden) {
            pollingTimeout = setTimeout(pollOrderStatus, POLLING_INTERVAL);
            return;
        }

        fetch(statusUrl, {
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        })
        .then(response => {
            if (response.status === 404) {
                // Order no longer exists
                if (connectionMsg) {
                    connectionMsg.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle-fill"></i> Order tracking unavailable</span>';
                }
                throw new Error("Order not found");
            }
            if (!response.ok) {
                throw new Error("Server response error");
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                // Reconnect message
                if (connectionMsg) {
                    connectionMsg.innerHTML = '<span class="text-success"><span class="spinner-grow spinner-grow-sm text-accent me-1" role="status"></span> Live status updates active</span>';
                }

                const currentStatus = data.status;
                const statusDisplay = data.status_display;

                updateStatusBadge(currentStatus, statusDisplay);

                if (currentStatus === "CANCELLED" || data.is_cancelled || data.is_terminal) {
                    const timelineEl = document.getElementById("order-timeline-steps");
                    const cancelledEl = document.getElementById("cancelled-state-notice");
                    if (timelineEl) timelineEl.classList.add("d-none");
                    if (cancelledEl) cancelledEl.classList.remove("d-none");
                    
                    if (connectionMsg) {
                        connectionMsg.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle-fill"></i> Order cancelled</span>';
                    }
                    // Stop polling
                    return;
                }

                updateOrderProgress(currentStatus);

                if (data.is_completed || currentStatus === "COMPLETED" || data.is_terminal) {
                    if (connectionMsg) {
                        connectionMsg.innerHTML = '<span class="text-muted"><i class="bi bi-check-circle-fill"></i> Order finished</span>';
                    }
                    // Stop polling
                    return;
                }
            }
            // Schedule next check
            pollingTimeout = setTimeout(pollOrderStatus, POLLING_INTERVAL);
        })
        .catch(err => {
            console.error("Tracking update error:", err);
            
            if (err.message === "Order not found") {
                // Permanent failure - stop polling
                return;
            }

            // Temporary network/server failure - notify user and keep retry scheduling
            if (connectionMsg) {
                connectionMsg.innerHTML = '<span class="text-warning"><i class="bi bi-exclamation-triangle-fill"></i> Connection issues. Retrying...</span>';
            }
            pollingTimeout = setTimeout(pollOrderStatus, POLLING_INTERVAL);
        });
    }

    // Initialize UI on page load
    updateStatusBadge(initialStatus, statusBadge ? statusBadge.textContent.trim() : "");
    updateOrderProgress(initialStatus);

    // Run polling loop if not already completed
    if (initialStatus !== "COMPLETED") {
        pollingTimeout = setTimeout(pollOrderStatus, POLLING_INTERVAL);
    } else {
        if (connectionMsg) {
            connectionMsg.innerHTML = '<span class="text-muted"><i class="bi bi-check-circle-fill"></i> Order finished</span>';
        }
    }
})();
