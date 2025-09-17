/**
 * School Manager - Calendar & Schedule JavaScript
 * Handles calendar interactions, schedule management, and drag-and-drop
 */

(function() {
    'use strict';

    function csrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    window.ScheduleCalendar = {
        init: function() {
            this.bindEvents();
            this.initCurrentTimeIndicator();
            this.initDragAndDrop();
            this.initViewToggle();
        },

        bindEvents: function() {
            const weekly = document.getElementById('weeklySchedule');
            if (!weekly) return;

            // Delegate clicks on schedule entries to open details
            weekly.addEventListener('click', (e) => {
                const entry = e.target.closest('.schedule-entry');
                if (entry && !e.target.closest('.btn')) {
                    const entryId = entry.dataset.entryId;
                    if (entryId) {
                        this.showEntryDetails(entryId);
                    }
                }
            });
        },

        initViewToggle: function() {
            const weekRadio = document.getElementById('weekView');
            const monthRadio = document.getElementById('monthView');
            const weekSection = document.querySelector('.schedule-calendar');
            const monthSection = document.getElementById('monthCalendar');
            const monthNav = document.getElementById('monthNav');
            if (!weekRadio || !monthRadio || !weekSection || !monthSection) return;

            const renderMonth = () => {
                // Build month grid using values from dataset or URL params
                const dsYear = parseInt(monthSection.dataset.year || '0', 10);
                const dsMonth = parseInt(monthSection.dataset.month || '0', 10); // 1..12
                const url = new URL(window.location);
                const y = parseInt(url.searchParams.get('year') || dsYear || (new Date().getFullYear()), 10);
                const m1 = parseInt(url.searchParams.get('month') || dsMonth || (new Date().getMonth() + 1), 10); // 1..12
                const year = y;
                const month = m1 - 1; // 0..11
                const first = new Date(year, month, 1);
                const last = new Date(year, month + 1, 0);
                const firstWeekday = (first.getDay() + 6) % 7; // 0=Luni
                const totalDays = last.getDate();

                // Clear previous cells (keep 7 headers already rendered in template)
                monthSection.querySelectorAll('.day-cell').forEach(el => el.remove());

                // Fill leading blanks
                for (let i = 0; i < firstWeekday; i++) {
                    const cell = document.createElement('div');
                    cell.className = 'day-cell other-month';
                    monthSection.appendChild(cell);
                }
                // Fill days
                for (let d = 1; d <= totalDays; d++) {
                    const cell = document.createElement('div');
                    cell.className = 'day-cell';
                    const num = document.createElement('div');
                    num.className = 'day-number';
                    num.textContent = d;
                    const events = document.createElement('div');
                    events.className = 'day-events';
                    const dayEvents = (window.SCHEDULE_MONTH_EVENTS || {})[d] || [];
                    // group count by subject
                    const subjCount = {};
                    dayEvents.forEach(ev => {
                        const evEl = document.createElement('a');
                        evEl.className = 'day-event';
                        evEl.style.setProperty('--event-color', ev.color || '#4facfe');
                        evEl.href = ev.url || '#';
                        evEl.textContent = (ev.subject ? ev.subject + ': ' : '') + ev.label;
                        events.appendChild(evEl);
                        if (ev.subject) subjCount[ev.subject] = (subjCount[ev.subject] || 0) + 1;
                    });
                    const subjNum = Object.keys(subjCount).length;
                    if (subjNum > 0) {
                        const counter = document.createElement('div');
                        counter.className = 'small text-muted mt-1';
                        counter.textContent = subjNum + ' materii în această zi';
                        events.appendChild(counter);
                    }
                    cell.appendChild(num);
                    cell.appendChild(events);
                    monthSection.appendChild(cell);
                }
            };

            const update = () => {
                if (monthRadio.checked) {
                    weekSection.classList.add('d-none');
                    monthSection.classList.remove('d-none');
                    if (monthNav) monthNav.classList.remove('d-none');
                    renderMonth();
                } else {
                    monthSection.classList.add('d-none');
                    weekSection.classList.remove('d-none');
                    if (monthNav) monthNav.classList.add('d-none');
                }
            };

            weekRadio.addEventListener('change', () => {
                const url = new URL(window.location);
                url.searchParams.set('view', 'week');
                window.history.replaceState({}, '', url);
                update();
            });
            monthRadio.addEventListener('change', () => {
                const url = new URL(window.location);
                url.searchParams.set('view', 'month');
                window.history.replaceState({}, '', url);
                update();
            });
            update();

            // Month navigation (client-side)
            if (monthNav) {
                document.getElementById('prevMonthBtn')?.addEventListener('click', () => this.navigateMonth(-1));
                document.getElementById('nextMonthBtn')?.addEventListener('click', () => this.navigateMonth(1));
            }
        },

        navigateMonth: function(delta) {
            const url = new URL(window.location);
            const currentMonth = parseInt(url.searchParams.get('month') || (monthSection.dataset.month || (new Date().getMonth() + 1)), 10);
            const currentYear = parseInt(url.searchParams.get('year') || (monthSection.dataset.year || (new Date().getFullYear())), 10);
            let m = currentMonth + delta;
            let y = currentYear;
            if (m < 1) { m = 12; y -= 1; }
            if (m > 12) { m = 1; y += 1; }
            url.searchParams.set('month', m);
            url.searchParams.set('year', y);
            // preserve view=month flag so page stays in monthly view
            url.searchParams.set('view', 'month');
            window.location.assign(url.toString());
        },

        showEntryDetails: function(entryId) {
            fetch(`/orar/entry/${entryId}/`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const modal = new bootstrap.Modal(document.getElementById('entryDetailsModal'));
                        document.getElementById('entryDetailsContent').innerHTML = data.html;
                        document.getElementById('editEntryBtn').onclick = () => window.location.href = `/orar/entry/${entryId}/edit/`;
                        modal.show();
                    }
                })
                .catch(() => SchoolManager.showAlert('Eroare la încărcarea detaliilor!', 'danger'));
        },

        initCurrentTimeIndicator: function() {
            // Re-draw indicator every minute
            this.updateIndicator();
            setInterval(() => this.updateIndicator(), 60000);
        },

        updateIndicator: function() {
            // This relies on server rendered cells and CSS .current-time-indicator
            const existing = document.querySelector('.current-time-indicator');
            if (existing) existing.remove();

            // Read schedule parameters provided by server
            const P = window.SCHEDULE_PARAMS || {};
            const startHour = parseInt(P.startHour ?? 8, 10);
            const startMinute = parseInt(P.startMinute ?? 0, 10);
            const durationMin = parseInt(P.durationMin ?? 50, 10);
            const breakMin = parseInt(P.breakMin ?? 10, 10);
            const maxHours = parseInt(P.maxHours ?? 8, 10);

            // Get now in Europe/Bucharest using Intl parts (robust against parsing differences)
            const parts = new Intl.DateTimeFormat('en-GB', {
                timeZone: 'Europe/Bucharest',
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            }).formatToParts(new Date());
            const get = (type) => parseInt(parts.find(p => p.type === type).value, 10);
            const tzNow = new Date(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'), 0);
            const day = tzNow.getDay(); // 0=Sun .. 6=Sat
            if (day < 1 || day > 5) return; // only Mon-Fri

            const dayStart = new Date(tzNow);
            dayStart.setHours(startHour, startMinute, 0, 0);

            const minutesSinceStart = Math.floor((tzNow - dayStart) / 60000);
            const slotTotal = durationMin + breakMin;
            if (minutesSinceStart < 0) return;
            if (minutesSinceStart > slotTotal * maxHours) return;

            const currentSlot = Math.min(maxHours, Math.max(1, Math.floor(minutesSinceStart / slotTotal) + 1));
            const minuteInSlot = Math.max(0, minutesSinceStart - (currentSlot - 1) * slotTotal);
            const minuteProgress = Math.min(minuteInSlot, durationMin) / durationMin;

            const cell = document.querySelector(`[data-day="${day}"][data-hour-number="${currentSlot}"]`);
            if (!cell) return;

            const indicator = document.createElement('div');
            indicator.className = 'current-time-indicator';
            indicator.style.top = (minuteProgress * 100) + '%';
            cell.style.position = 'relative';
            cell.appendChild(indicator);
        },

        initDragAndDrop: function() {
            const entries = document.querySelectorAll('.schedule-entry');
            entries.forEach(el => {
                el.setAttribute('draggable', 'true');
                el.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', el.dataset.entryId);
                });
            });

            const cells = document.querySelectorAll('.hour-cell');
            cells.forEach(cell => {
                cell.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    cell.classList.add('drag-over');
                });
                cell.addEventListener('dragleave', () => cell.classList.remove('drag-over'));
                cell.addEventListener('drop', (e) => {
                    e.preventDefault();
                    cell.classList.remove('drag-over');
                    const entryId = e.dataTransfer.getData('text/plain');
                    const newDay = parseInt(cell.dataset.day, 10);
                    const newHour = parseInt(cell.dataset.hourNumber, 10);
                    this.moveEntry(entryId, newDay, newHour);
                });
            });
        },

        moveEntry: function(entryId, newDay, newHour) {
            const formData = new FormData();
            formData.append('action', 'move_entry');
            formData.append('entry_id', entryId);
            formData.append('new_day', newDay);
            formData.append('new_hour', newHour);
            formData.append('csrfmiddlewaretoken', csrfToken());

            fetch('/orar/quick-edit/', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    SchoolManager.showAlert(data.message || 'Ora a fost mutată!', 'success');
                    setTimeout(() => window.location.reload(), 400);
                } else {
                    SchoolManager.showAlert(data.error || 'Mutare eșuată!', 'danger');
                }
            })
            .catch(() => SchoolManager.showAlert('Eroare de rețea!', 'danger'));
        }
    };

    document.addEventListener('DOMContentLoaded', function() {
        if (typeof ScheduleCalendar !== 'undefined') {
            ScheduleCalendar.init();
        }
    });
})();