(function ($) {
    const log = function() {};

    const e$ = $('input[name="end"]');
    const s$ = $('input[name="start"]');
    const uid$ = $('select[name="user"]');
    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
    const spinner$ = $('#submitspinner');
    const overlappingcontainer$ = $('#overlappingcontainer');

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
        overlappingcontainer$.hide();
        tbody$ = $('tbody', overlappingcontainer$);
        tbody$.empty();

        if (!data || !data.mods || data.mods.length === 0) {
            return
        }
        overlappingcontainer$.show();

        let newrow;
        data.mods.forEach(element => {
            newrow = ''
            newrow += '<tr>';
            newrow += '<td scope="row">' + element.item.id + '</td>'
            newrow += '<td>' + element.item.start + '</td>'
            newrow += '<td>' + element.item.end + '</td>'
            newrow += '<td>' + overlapactionsselection(element.item.id, element.res) + '</td>'
            newrow += '</tr>';
            tbody$.append(newrow);
        });
    }

    function queryForConflicts() {
        spinner$.show();
        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        const startDate = s$.datepicker('getDate');
        if (!startDate) {
            spinner$.hide();
            return;
        }

        const endDate = e$.datepicker('getDate') || startDate;
        log("query for conflicts", startDate, endDate);

        $.ajax({
            url: wamytmroot + 'check',
            method: "POST",
            beforeSend: function (xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            },
            data: {
                start: dateToPostStr(startDate),
                end: dateToPostStr(endDate),
                uid: uid$.val()
            },
            xhrFields: {
                withCredentials: true
            }
        }).done(updateTable)
            .fail(console.error)
            .always(function () {
                log("complete");
                spinner$.hide();
            });;
    }

    s$.datepicker().on('changeDate', function (e) {
        e$.datepicker('setStartDate', (s$.datepicker('getDate')));
    });
    e$.datepicker().on('changeDate', function (e) {
        s$.datepicker('setEndDate', (e$.datepicker('getDate')));
    });
    s$.on('change', queryForConflicts);
    e$.on('change', queryForConflicts);
    uid$.on('change', queryForConflicts);


})(jQuery)
