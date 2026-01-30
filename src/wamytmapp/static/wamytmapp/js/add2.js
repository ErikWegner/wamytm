class WordCount extends HTMLTableRowElement {
    constructor() {
        super();
        this.appendChild(document.createElement('td')).scope = "row";
        [...Array(5).keys()].map(e => this.appendChild(document.createElement('td')));
    }
    setData(p_val) {
        Array.from(this.children).map((e, n) => e.innerHTML = p_val[n]);
    }
}
customElements.define('word-count', WordCount, { extends: "tr" });

(function ($) {
    const log = function () { };

    const e$ = $('input[name="end"]');
    const e2$ = document.getElementById('end-hidden');
    const s$ = $('input[name="start"]');
    const s2$ = document.getElementById('start-hidden');
    const uid$ = document.getElementsByName('user')[0];
    const part$ = document.getElementsByName('part_of_day')[0];
    const kind$ = document.getElementsByName('kind')[0];
    const desc$ = document.getElementsByName('description')[0];
    const org$ = document.getElementById('id_org_id');

    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
    const spinner$ = document.getElementById('submitspinner');
    const overlappingcontainer$ = document.getElementById('overlappingcontainer');

    function overlapactionsselection(id, res) {
        const restxt = wamytmi18n['res_' + res];
        return ('<input checked="" class="overlapaction" type="checkbox" data-trid="' +
            id + '" name="overlap_actions" value="' + id + ':' + res + '"> ' + restxt)
    }

    function dateToPostStr(date) {
        var localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60 * 1000);
        return localDate.toISOString().substring(0, 10);
    }

    function updateTable(data) {
        org$.value = data.org_id
        overlappingcontainer$.style.display = (!data || !data.mods || data.mods.length === 0) ? 'none' : '';

        let tbody$ = document.querySelector('#overlappingcontainer table tbody');
        while (tbody$.firstChild) tbody$.removeChild(tbody$.firstChild);

        data.mods.forEach(e => {
            tbody$.appendChild(document.createElement('tr', { is: 'word-count' })).setData([e.item.id, e.item.start, e.item.end, e.item.kind, e.item.partial, overlapactionsselection(e.item.id, e.res)]);
        });
    }

    function queryForConflicts() {
        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        const startDateStr = s2$.value;
        if (!startDateStr) {
            spinner$.style.display = 'none';
            $.ajax({
                url: wamytmroot + 'getorgid',
                method: "POST",
                beforeSend: function (xhr, settings) {
                    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    }
                },
                data: {
                    uid: uid$.value
                },
                xhrFields: {
                    withCredentials: true
                }
            }).done(function (data) {
                org$.value = data.org_id;
            }).fail(console.error)
                .always(function () {
                    return;
                });

        } else {
            spinner$.style.display = '';
        }

        const endDateStr = e2$.value || startDateStr;
        log("query for conflicts", startDateStr, endDateStr);

        $.ajax({
            url: wamytmroot + 'check',
            method: "POST",
            beforeSend: function (xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            },
            data: {
                start: startDateStr,
                end: endDateStr,
                uid: uid$.value,
                kind: kind$.value[0],
                part: part$.value
            },
            xhrFields: {
                withCredentials: true
            }
        }).done(updateTable)
            .fail(console.error)
            .always(function () {
                log("complete");

                spinner$.style.display = 'none';
            });
    }

    s2$.onchange = queryForConflicts;
    e2$.onchange = queryForConflicts;
    uid$.addEventListener('change', queryForConflicts);
    part$.addEventListener('change', queryForConflicts);
    kind$.onchange = queryForConflicts;
    desc$.onchange = queryForConflicts;
})(jQuery);

// Custom Date Range Picker
(function() {
    'use strict';
    
    const monthNames = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 
                        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    const dayNames = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
    
    let startDate = null;
    let endDate = null;
    let isInitialState = true;
    let currentMonth = new Date();
    let pickerElement = null;
    let isOpen = false;
    
    function formatDate(date) {
        if (!date) return '';
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${day}.${month}.${year}`;
    }
    
    function formatDateISO(date) {
        if (!date) return '';
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    function updateDisplay() {
        document.getElementById('picker-start-display').value = formatDate(startDate);
        document.getElementById('picker-end-display').value = formatDate(endDate);
        document.getElementById('start-hidden').value = formatDateISO(startDate);
        document.getElementById('end-hidden').value = formatDateISO(endDate || startDate);
        
        // Trigger change event for conflict checking
        const startHidden = document.getElementById('start-hidden');
        const endHidden = document.getElementById('end-hidden');
        startHidden.dispatchEvent(new Event('change', { bubbles: true }));
        endHidden.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    function isSameDay(date1, date2) {
        if (!date1 || !date2) return false;
        return date1.getFullYear() === date2.getFullYear() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getDate() === date2.getDate();
    }
    
    function isInRange(date) {
        if (!startDate || !endDate) return false;
        return date >= startDate && date <= endDate;
    }
    
    function renderCalendar() {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const prevLastDay = new Date(year, month, 0);
        
        // Start on Monday
        const firstDayWeekday = (firstDay.getDay() + 6) % 7;
        
        let html = '<table><thead><tr>';
        dayNames.forEach(day => {
            html += `<th>${day}</th>`;
        });
        html += '</tr></thead><tbody><tr>';
        
        // Previous month days
        for (let i = firstDayWeekday - 1; i >= 0; i--) {
            const day = prevLastDay.getDate() - i;
            html += `<td><button type="button" class="daterangepicker-day disabled">${day}</button></td>`;
        }
        
        // Current month days
        const today = new Date();
        for (let day = 1; day <= lastDay.getDate(); day++) {
            if ((firstDayWeekday + day - 1) % 7 === 0 && day !== 1) {
                html += '</tr><tr>';
            }
            
            const date = new Date(year, month, day);
            let classes = 'daterangepicker-day';
            
            if (isSameDay(date, today)) {
                classes += ' today';
            }

            if (isSameDay(date, startDate)) {
                classes += ' start-date';
            } else if (isSameDay(date, endDate)) {
                classes += ' end-date';
            }
            if (isSameDay(date, startDate) || isSameDay(date, endDate)) {
                classes += ' selected';
            } else if (isInRange(date)) {
                classes += ' in-range';
            }
            
            html += `<td><button type="button" class="${classes}" data-date="${formatDateISO(date)}">${day}</button></td>`;
        }
        
        // Next month days to fill the row
        const remainingCells = (7 - ((firstDayWeekday + lastDay.getDate()) % 7)) % 7;
        for (let day = 1; day <= remainingCells; day++) {
            html += `<td><button type="button" class="daterangepicker-day disabled">${day}</button></td>`;
        }
        
        html += '</tr></tbody></table>';
        
        return html;
    }
    
    function updatePickerCalendar() {
        document.getElementById('month-year').textContent = 
            monthNames[currentMonth.getMonth()] + ' ' + currentMonth.getFullYear();
        document.getElementById('calendar').innerHTML = renderCalendar();
        updateDisplay();
    }
    
    function attachPickerEvents() {
        document.getElementById('prev-month').addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() - 1);
            updatePickerCalendar();
        });
        
        document.getElementById('next-month').addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() + 1);
            updatePickerCalendar();
        });
        
        document.getElementById('calendar').addEventListener('click', (e) => {
            if (e.target.classList.contains('daterangepicker-day') && 
                !e.target.classList.contains('disabled')) {
                const dateStr = e.target.getAttribute('data-date');
                const parts = dateStr.split('-');
                const selectedDate = new Date(parts[0], parts[1] - 1, parts[2]);
                
                if (!startDate) {
                    // First click ever: set start date
                    startDate = selectedDate;
                    endDate = null;
                    isInitialState = false;
                } else if (startDate && (!endDate || isInitialState)) {
                    // Start is set, but no end yet (OR initial state): set end date
                    if (selectedDate < startDate) {
                        // Selected before start, swap them
                        endDate = startDate;
                        startDate = selectedDate;
                    } else {
                        // Normal case: end after start
                        endDate = selectedDate;
                    }
                    isInitialState = false;
                } else if (startDate && endDate) {
                    // Both are set, start new selection
                    startDate = selectedDate;
                    endDate = null;
                    isInitialState = false;
                }
                
                updatePickerCalendar();
            }
        });
    }
    
    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
        // Set today as default
        const today = new Date();
        startDate = today;
        endDate = today;
        isInitialState = true;
        
        // Initialize calendar display
        updatePickerCalendar();
        attachPickerEvents();
    });
})();