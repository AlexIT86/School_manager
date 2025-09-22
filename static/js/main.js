/**
 * School Manager - Main JavaScript
 * Handles global functionality and interactions
 */

(function() {
    'use strict';

    // Global App Object
    window.SchoolManager = {
        init: function() {
            this.initializeComponents();
            this.bindEvents();
            this.loadUserPreferences();
            this.initializeNotifications();
            this.setupPerformanceOptimizations();
        },

        // Initialize all components
        initializeComponents: function() {
            this.initTooltips();
            this.initPopovers();
            this.initModals();
            this.initProgressBars();
            this.initCounters();
            this.initSearchFunctionality();
            this.initQuickActions();
            this.initFormValidation();
            this.initFileUploads();
            // Dark mode disabled
        },

        // Initialize Bootstrap tooltips
        initTooltips: function() {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl, {
                    delay: { show: 500, hide: 100 }
                });
            });
        },

        // Initialize Bootstrap popovers
        initPopovers: function() {
            const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
            popoverTriggerList.map(function(popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl, {
                    container: 'body'
                });
            });
        },

        // Initialize modals with custom events
        initModals: function() {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                modal.addEventListener('shown.bs.modal', function() {
                    const firstInput = this.querySelector('input, textarea, select');
                    if (firstInput) {
                        firstInput.focus();
                    }
                });

                modal.addEventListener('hidden.bs.modal', function() {
                    const form = this.querySelector('form');
                    if (form) {
                        form.reset();
                    }
                });
            });
        },

        // Animate progress bars
        initProgressBars: function() {
            const progressBars = document.querySelectorAll('.progress-bar');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const progressBar = entry.target;
                        const width = progressBar.getAttribute('aria-valuenow');
                        progressBar.style.width = width + '%';
                    }
                });
            }, { threshold: 0.1 });

            progressBars.forEach(bar => {
                bar.style.width = '0%';
                observer.observe(bar);
            });
        },

        // Animate counters
        initCounters: function() {
            const counters = document.querySelectorAll('[data-counter]');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.animateCounter(entry.target);
                    }
                });
            }, { threshold: 0.1 });

            counters.forEach(counter => observer.observe(counter));
        },

        animateCounter: function(element) {
            const target = parseInt(element.getAttribute('data-counter'));
            const duration = parseInt(element.getAttribute('data-duration')) || 2000;
            const startTime = performance.now();
            const startValue = 0;

            const updateCounter = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const value = Math.floor(startValue + (target - startValue) * this.easeOutQuart(progress));
                
                element.textContent = value;
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                }
            };

            requestAnimationFrame(updateCounter);
        },

        easeOutQuart: function(t) {
            return 1 - (--t) * t * t * t;
        },

        // Global search functionality
        initSearchFunctionality: function() {
            const searchInputs = document.querySelectorAll('.search-input, input[type="search"]');
            searchInputs.forEach(input => {
                let searchTimeout;
                input.addEventListener('input', function() {
                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(() => {
                        SchoolManager.performSearch(this.value, this.dataset.target);
                    }, 300);
                });
            });
        },

        performSearch: function(query, target) {
            if (!target) return;
            
            const items = document.querySelectorAll(target);
            const searchTerm = query.toLowerCase();

            items.forEach(item => {
                const searchableText = item.textContent.toLowerCase();
                const shouldShow = searchableText.includes(searchTerm);
                
                item.style.display = shouldShow ? 'block' : 'none';
                
                // Add highlighting
                if (shouldShow && searchTerm) {
                    this.highlightSearchTerm(item, searchTerm);
                } else {
                    this.removeHighlight(item);
                }
            });
        },

        highlightSearchTerm: function(element, term) {
            const walker = document.createTreeWalker(
                element,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            const textNodes = [];
            let node;
            while (node = walker.nextNode()) {
                textNodes.push(node);
            }

            textNodes.forEach(textNode => {
                const parent = textNode.parentNode;
                if (parent.tagName === 'MARK') return;
                
                const text = textNode.textContent;
                const regex = new RegExp(`(${term})`, 'gi');
                
                if (regex.test(text)) {
                    const highlightedHTML = text.replace(regex, '<mark class="search-highlight">$1</mark>');
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = highlightedHTML;
                    
                    while (tempDiv.firstChild) {
                        parent.insertBefore(tempDiv.firstChild, textNode);
                    }
                    parent.removeChild(textNode);
                }
            });
        },

        removeHighlight: function(element) {
            const highlights = element.querySelectorAll('.search-highlight');
            highlights.forEach(highlight => {
                const parent = highlight.parentNode;
                parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
                parent.normalize();
            });
        },

        // Quick actions functionality
        initQuickActions: function() {
            const quickActionsBtn = document.querySelector('.quick-actions .btn');
            if (quickActionsBtn) {
                quickActionsBtn.addEventListener('click', function() {
                    this.classList.add('pulse');
                    setTimeout(() => this.classList.remove('pulse'), 300);
                });
            }

            // Handle quick action items
            const quickActionItems = document.querySelectorAll('.quick-actions .dropdown-item');
            quickActionItems.forEach(item => {
                item.addEventListener('click', function(e) {
                    const href = this.getAttribute('href');
                    if (href && href.startsWith('/')) {
                        e.preventDefault();
                        SchoolManager.navigateWithLoading(href);
                    }
                });
            });
        },

        // Enhanced form validation
        initFormValidation: function() {
            const forms = document.querySelectorAll('form[data-validate]');
            forms.forEach(form => {
                form.addEventListener('submit', function(e) {
                    if (!SchoolManager.validateForm(this)) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                    this.classList.add('was-validated');
                });

                // Real-time validation
                const inputs = form.querySelectorAll('input, textarea, select');
                inputs.forEach(input => {
                    input.addEventListener('blur', function() {
                        SchoolManager.validateField(this);
                    });
                });
            });
        },

        validateForm: function(form) {
            let isValid = true;
            const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
            
            inputs.forEach(input => {
                if (!this.validateField(input)) {
                    isValid = false;
                }
            });

            return isValid;
        },

        validateField: function(field) {
            const value = field.value.trim();
            const type = field.type;
            let isValid = true;
            let message = '';

            // Required validation
            if (field.hasAttribute('required') && !value) {
                isValid = false;
                message = 'Acest câmp este obligatoriu.';
            }

            // Type-specific validation
            if (value && type === 'email') {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) {
                    isValid = false;
                    message = 'Introduceți o adresă de email validă.';
                }
            }

            if (value && type === 'tel') {
                const phoneRegex = /^[\d\s\-\+\(\)]{10,}$/;
                if (!phoneRegex.test(value)) {
                    isValid = false;
                    message = 'Introduceți un număr de telefon valid.';
                }
            }

            // Update field state
            field.classList.toggle('is-valid', isValid);
            field.classList.toggle('is-invalid', !isValid);

            // Show/hide feedback
            let feedback = field.parentNode.querySelector('.invalid-feedback');
            if (!isValid && !feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                field.parentNode.appendChild(feedback);
            }
            
            if (feedback) {
                feedback.textContent = message;
                feedback.style.display = isValid ? 'none' : 'block';
            }

            return isValid;
        },

        // File upload handling
        initFileUploads: function() {
            const fileInputs = document.querySelectorAll('input[type="file"]');
            fileInputs.forEach(input => {
                input.addEventListener('change', function() {
                    SchoolManager.handleFileUpload(this);
                });
            });
        },

        handleFileUpload: function(input) {
            const files = input.files;
            const maxSize = 10 * 1024 * 1024; // 10MB
            const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain'];

            Array.from(files).forEach(file => {
                // Size validation
                if (file.size > maxSize) {
                    this.showAlert('Fișierul este prea mare. Mărimea maximă permisă este 10MB.', 'danger');
                    input.value = '';
                    return;
                }

                // Type validation
                if (!allowedTypes.includes(file.type)) {
                    this.showAlert('Tipul de fișier nu este permis.', 'danger');
                    input.value = '';
                    return;
                }

                // Show preview for images
                if (file.type.startsWith('image/')) {
                    this.showImagePreview(file, input);
                }
            });
        },

        showImagePreview: function(file, input) {
            const reader = new FileReader();
            reader.onload = function(e) {
                let preview = input.parentNode.querySelector('.image-preview');
                if (!preview) {
                    preview = document.createElement('div');
                    preview.className = 'image-preview mt-2';
                    input.parentNode.appendChild(preview);
                }
                
                preview.innerHTML = `
                    <img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">
                    <button type="button" class="btn btn-sm btn-danger ms-2" onclick="this.parentNode.remove();">
                        <i class="fas fa-times"></i>
                    </button>
                `;
            };
            reader.readAsDataURL(file);
        },

        // Theme toggle disabled
        initThemeToggle: function() {},
        toggleTheme: function() {},

        // Notification system
        initializeNotifications: function() {
            if (window.DISABLE_TOASTS || document.body.dataset.noToasts === '1') {
                return; // Skip notifications on pages that opt-out (e.g., Chat)
            }
            this.checkForNewNotifications();
            setInterval(() => this.checkForNewNotifications(), 60000); // Check every minute
        },

        checkForNewNotifications: function() {
            fetch('/api/notifications/unread/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(response => {
                    if (!response.ok) {
                        // Endpoint inexistent sau nereușit – nu afișăm eroare în consolă
                        return { count: 0, new_notifications: [] };
                    }
                    return response.json().catch(() => ({ count: 0, new_notifications: [] }));
                })
                .then(data => {
                    // Dacă am primit un obiect Response transformat manual, asigură structura
                    const payload = data && typeof data === 'object' ? data : { count: 0, new_notifications: [] };
                    this.updateNotificationBadge(payload.count || 0);
                    if (Array.isArray(payload.new_notifications) && payload.new_notifications.length) {
                        this.showNewNotifications(payload.new_notifications);
                    }
                })
                .catch(() => { /* Ignorăm complet erorile de rețea/JSON pentru a evita zgomotul în consolă */ });
        },

        updateNotificationBadge: function(count) {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        },

        showNewNotifications: function(notifications) {
            notifications.forEach(notification => {
                this.showToast(notification.title, notification.message, notification.type);
            });
        },

        // Toast notifications
        showToast: function(title, message, type = 'info') {
            if (window.DISABLE_TOASTS || document.body.dataset.noToasts === '1') {
                return;
            }
            const toastContainer = this.getToastContainer();
            const toastId = 'toast-' + Date.now();
            
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = `toast align-items-center text-white bg-${type} border-0`;
            toast.setAttribute('role', 'alert');
            
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            
            toastContainer.appendChild(toast);
            
            const bsToast = new bootstrap.Toast(toast, {
                delay: 5000
            });
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', function() {
                this.remove();
            });
        },

        getToastContainer: function() {
            if (window.DISABLE_TOASTS || document.body.dataset.noToasts === '1') {
                return null;
            }
            let container = document.querySelector('.toast-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                container.style.zIndex = '1100';
                document.body.appendChild(container);
            }
            return container;
        },

        // Alert system
        showAlert: function(message, type = 'info', duration = 5000) {
            const alertContainer = this.getAlertContainer();
            const alertId = 'alert-' + Date.now();
            
            const alert = document.createElement('div');
            alert.id = alertId;
            alert.className = `alert alert-${type} alert-dismissible fade show`;
            alert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            alertContainer.appendChild(alert);
            
            if (duration > 0) {
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, duration);
            }
        },

        getAlertContainer: function() {
            let container = document.querySelector('.alert-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'alert-container position-fixed top-0 start-50 translate-middle-x';
                container.style.zIndex = '1100';
                container.style.marginTop = '100px';
                document.body.appendChild(container);
            }
            return container;
        },

        // Navigation with loading
        navigateWithLoading: function(url) {
            this.showLoadingOverlay();
            window.location.href = url;
        },

        showLoadingOverlay: function() {
            let overlay = document.querySelector('.loading-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'loading-overlay';
                overlay.innerHTML = `
                    <div class="loading-content">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-3">Se încarcă...</p>
                    </div>
                `;
                document.body.appendChild(overlay);
            }
            overlay.style.display = 'flex';
        },

        hideLoadingOverlay: function() {
            const overlay = document.querySelector('.loading-overlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        },

        // User preferences
        loadUserPreferences: function() {
            const preferences = localStorage.getItem('schoolManagerPreferences');
            if (preferences) {
                try {
                    const prefs = JSON.parse(preferences);
                    this.applyPreferences(prefs);
                } catch (error) {
                    console.error('Error loading preferences:', error);
                }
            }
        },

        saveUserPreference: function(key, value) {
            const preferences = JSON.parse(localStorage.getItem('schoolManagerPreferences') || '{}');
            preferences[key] = value;
            localStorage.setItem('schoolManagerPreferences', JSON.stringify(preferences));
        },

        applyPreferences: function(preferences) {
            // Apply font size
            if (preferences.fontSize) {
                document.documentElement.style.fontSize = preferences.fontSize;
            }
            
            // Apply other preferences...
        },

        // Performance optimizations
        setupPerformanceOptimizations: function() {
            // Lazy load images
            this.initLazyLoading();
            
            // Debounce resize events
            let resizeTimeout;
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    SchoolManager.handleResize();
                }, 250);
            });
        },

        initLazyLoading: function() {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        },

        handleResize: function() {
            // Handle responsive adjustments
            const isMobile = window.innerWidth < 768;
            document.body.classList.toggle('mobile-view', isMobile);
        },

        // Bind global events
        bindEvents: function() {
            // Handle escape key to close modals/dropdowns
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    const openModal = document.querySelector('.modal.show');
                    if (openModal) {
                        bootstrap.Modal.getInstance(openModal).hide();
                    }
                }
            });

            // Handle form submissions with loading states
            document.addEventListener('submit', function(e) {
                const form = e.target;
                if (form.tagName === 'FORM') {
                    // Skip global loading for forms that opt-out
                    if (form.hasAttribute('data-no-global-loading')) {
                        return;
                    }
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        SchoolManager.setButtonLoading(submitBtn, true);
                    }
                }
            });

            // Handle AJAX form submissions
            document.addEventListener('click', function(e) {
                if (e.target.matches('[data-ajax-form]')) {
                    e.preventDefault();
                    SchoolManager.submitAjaxForm(e.target.closest('form'));
                }
            });
        },

        setButtonLoading: function(button, loading) {
            if (loading) {
                button.dataset.originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Se încarcă...';
                button.disabled = true;
            } else {
                button.innerHTML = button.dataset.originalText;
                button.disabled = false;
            }
        },

        submitAjaxForm: function(form) {
            const formData = new FormData(form);
            const url = form.action || window.location.href;
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showAlert(data.message || 'Operația a fost realizată cu succes!', 'success');
                    if (data.redirect) {
                        setTimeout(() => window.location.href = data.redirect, 1000);
                    }
                } else {
                    this.showAlert(data.error || 'A apărut o eroare!', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('A apărut o eroare de rețea!', 'danger');
            });
        },

        // Utility functions
        formatDate: function(date, format = 'dd.mm.yyyy') {
            const d = new Date(date);
            const day = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year = d.getFullYear();
            
            return format
                .replace('dd', day)
                .replace('mm', month)
                .replace('yyyy', year);
        },

        formatTime: function(date) {
            return new Date(date).toLocaleTimeString('ro-RO', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Skip init notifications if on chat pages
        if (location.pathname.startsWith('/chat/')) {
            document.body.dataset.noToasts = '1';
            window.DISABLE_TOASTS = true;
        }
        SchoolManager.init();
        // Hide loading overlay if present
        setTimeout(() => SchoolManager.hideLoadingOverlay(), 500);
    });

    // Handle page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            SchoolManager.checkForNewNotifications();
        }
    });

})();

// Additional loading styles
const loadingStyles = `
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(5px);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.loading-content {
    text-align: center;
    color: #6c757d;
}

.search-highlight {
    background-color: #fff3cd;
    padding: 0 2px;
    border-radius: 2px;
}

.pulse {
    animation: pulse 0.3s ease-in-out;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); }
}

.mobile-view .quick-actions {
    bottom: 20px;
    right: 20px;
}

.mobile-view .quick-actions .btn {
    width: 50px;
    height: 50px;
}
`;

// Inject styles
const styleSheet = document.createElement('style');
styleSheet.textContent = loadingStyles;
document.head.appendChild(styleSheet);