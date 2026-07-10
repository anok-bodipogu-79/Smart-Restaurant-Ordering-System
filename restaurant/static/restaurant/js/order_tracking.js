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
    const etaContainer = document.getElementById("eta-container");
    const etaText = document.getElementById("eta-text");
    const etaTimeStamp = document.getElementById("eta-time-stamp");
    const etaReadyTime = document.getElementById("eta-ready-time");

    function updateEtaDisplay(data) {
        if (!etaContainer) return;
        
        if (data.status === "COMPLETED" || data.status === "CANCELLED" || data.is_terminal) {
            etaContainer.classList.add("d-none");
            return;
        }

        etaContainer.classList.remove("d-none");

        if (data.is_delayed) {
            etaText.innerHTML = '<span class="text-danger fw-bold"><i class="bi bi-hourglass-split me-1"></i> Delayed: We are currently working hard on your order!</span>';
            if (etaTimeStamp) etaTimeStamp.classList.add("d-none");
        } else if (data.estimated_prep_minutes) {
            etaText.innerHTML = `<span class="text-success fw-bold"><i class="bi bi-clock me-1"></i> Ready in approx. ${data.estimated_prep_minutes} mins</span>`;
            if (etaTimeStamp) {
                etaTimeStamp.classList.remove("d-none");
                if (etaReadyTime) {
                    const createdAtStr = trackingPanel.dataset.createdAt;
                    if (createdAtStr) {
                        const createdAt = new Date(createdAtStr);
                        const readyTime = new Date(createdAt.getTime() + data.estimated_prep_minutes * 60000);
                        let options = { hour: '2-digit', minute: '2-digit', hour12: true };
                        etaReadyTime.textContent = readyTime.toLocaleTimeString([], options);
                    } else {
                        etaReadyTime.textContent = data.estimated_ready_time || "--:--";
                    }
                }
            }
        } else {
            etaText.textContent = "Estimated preparation time not assigned yet.";
            if (etaTimeStamp) etaTimeStamp.classList.add("d-none");
        }
    }

    // Whitelist CSS styles for order status badges — new Premium Hospitality colors
    const BADGE_STYLES = {
        "RECEIVED":  { bg: "#F1F5F9", color: "#475569", border: "1px solid #E2E8F0" },
        "PREPARING": { bg: "#FEF3C7", color: "#92400E", border: "1px solid #FDE68A" },
        "READY":     { bg: "#DCFCE7", color: "#15803D", border: "1px solid #BBF7D0" },
        "COMPLETED": { bg: "#ECFDF5", color: "#065F46", border: "1px solid #A7F3D0" },
        "CANCELLED": { bg: "#FEE4E2", color: "#B42318", border: "1px solid #FECACA" }
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
                // Completed steps — Forest Green
                iconWrapper.style.background = "#E6EEE9";
                iconWrapper.style.borderColor = "#173F35";
                iconWrapper.style.color = "#173F35";
                label.style.color = "#173F35";
                label.style.fontWeight = "700";
            } else if (idx === currentIdx) {
                // Current active step
                iconWrapper.classList.add("neumorphic-active");
                iconWrapper.style.background = "var(--surface-primary)";
                iconWrapper.style.borderColor = "transparent";
                
                if (status === "RECEIVED") {
                    iconWrapper.style.color = "var(--text-primary)";
                    label.style.color = "var(--text-primary)";
                } else if (status === "PREPARING") {
                    iconWrapper.style.color = "var(--accent-gold)";
                    label.style.color = "var(--accent-gold)";
                } else if (status === "READY" || status === "COMPLETED") {
                    iconWrapper.style.color = "var(--brand-primary)";
                    label.style.color = "var(--brand-primary)";
                }
                label.style.fontWeight = "700";
            } else {
                // Pending steps
                iconWrapper.style.background = "#F7F6F2";
                iconWrapper.style.borderColor = "#E7E5E0";
                iconWrapper.style.color = "#A8A29E";
                label.style.color = "#A8A29E";
                label.style.fontWeight = "600";
            }
        });
    }

    /**
     * Updates status badge text and visual styling.
     */
    function updateStatusBadge(status, statusDisplay) {
        if (!statusBadge) return;

        statusBadge.textContent = statusDisplay;

        // Apply inline styles from our new design system
        const style = BADGE_STYLES[status] || { bg: "#F1F5F9", color: "#475569", border: "1px solid #E2E8F0" };
        statusBadge.style.backgroundColor = style.bg;
        statusBadge.style.color = style.color;
        statusBadge.style.border = "none";
        statusBadge.classList.add("clay-badge");
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
                updateEtaDisplay(data);

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

    const initialEta = {
        status: initialStatus,
        is_terminal: initialStatus === "COMPLETED" || initialStatus === "CANCELLED",
        is_delayed: trackingPanel.dataset.isDelayed === "true",
        estimated_prep_minutes: trackingPanel.dataset.prepMinutes ? parseInt(trackingPanel.dataset.prepMinutes, 10) : null,
        estimated_ready_time: trackingPanel.dataset.readyTime || ""
    };
    updateEtaDisplay(initialEta);

    // Run polling loop if not already completed
    if (initialStatus !== "COMPLETED") {
        pollingTimeout = setTimeout(pollOrderStatus, POLLING_INTERVAL);
    } else {
        if (connectionMsg) {
            connectionMsg.innerHTML = '<span class="text-muted"><i class="bi bi-check-circle-fill"></i> Order finished</span>';
        }
    }
})();
