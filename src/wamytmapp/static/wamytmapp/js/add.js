(function ($) {

    const e$ = $('input[name="end"]');
    const s$ = $('input[name="start"]');
    const oa$ = $('input[name="id_overlap_actions"]');
    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
    const spinner$ = $('#submitspinner');
    const overlappingcontainer$ = $('#overlappingcontainer');

    function overlapactionsselection(id, res) {
        const restxt = wamytmi18n['res_' + res];
        return ('<input class="overlapaction" type="checkbox" data-trid="' + id + '"> ' + restxt)
    }

    function updateTable(data) {
        oa$.val("");
        if (!data || !data.mods || data.mods.length === 0) {
            overlappingcontainer$.hide();
            return
        }
        overlappingcontainer$.show();

        tbody$ = $('tbody', overlappingcontainer$);
        tbody$.empty();

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
        console.log("query for conflicts", startDate, endDate);

        $.ajax({
            url: wamytmroot + 'check',
            method: "POST",
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            },
            data: {
                start: startDate.toISOString().substring(0, 10),
                end: endDate.toISOString().substring(0, 10),
            },
            xhrFields: {
                withCredentials: true
            }}).done(updateTable)
              .fail(console.error)
              .always(function() {
                console.log( "complete" );
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


})(jQuery)
