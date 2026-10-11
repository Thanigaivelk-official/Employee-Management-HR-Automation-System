/**
 * Main JavaScript file for Employee Management & HR Automation System
 */
document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Toggle for Mobile / Responsive views
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const sidebarWrapper = document.getElementById('sidebar-wrapper');
    if (sidebarToggleBtn && sidebarWrapper) {
        sidebarToggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            sidebarWrapper.classList.toggle('toggled');
        });
    }

    // 2. Auto-dismiss Alert messages after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 3. Confirm Dialog for Destructive / Confirmation buttons
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function (button) {
        button.addEventListener('click', function (e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure you want to proceed with this action?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // 4. Live Clock Widget (if element present)
    const liveClockEl = document.getElementById('live-clock');
    if (liveClockEl) {
        function updateClock() {
            const now = new Date();
            liveClockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        updateClock();
        setInterval(updateClock, 1000);
    }
});
