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
})(jQuery)
