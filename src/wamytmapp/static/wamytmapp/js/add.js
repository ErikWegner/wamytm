class WordCount extends HTMLTableRowElement {
    constructor() {
      super();
      this.appendChild(document.createElement('td')).scope = "row";
      [...Array(3).keys()].map(e=>this.appendChild(document.createElement('td')));
    }
    setData(p_val) {
        Array.from(this.children).map((e,n) => e.innerHTML=p_val[n]);
    }
}
customElements.define('word-count', WordCount, {extends: "tr"});

function getXHRRequestPromise(body) {
	return new Promise(function(resolve, reject) {
		var xhr = new XMLHttpRequest();
		xhr.open('POST', wamytmroot + 'check');
        xhr.withCredentials = true;
		xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
		xhr.send(JSON.stringify(body));
		xhr.onreadystatechange = function() {
			if (xhr.readyState === 4 && xhr.status === 204) {
				resolve(xhr.getResponseHeader(desiredHeader));
			} else {
				reject({
                   status: this.status,
                   statusText: xhr.statusText
                 });
			}
		};
	});
}

(function ($) {
    const log = function() {};

    const e$ = $('input[name="end"]');
    const s$ = $('input[name="start"]');
    const uid$ = $('select[name="user"]');
    const part$ = $('select[name="part_of_day"]');
    const kind$ = $('select[name="kind"]');
    const desc$ = $('input[name="description"]');
    
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
        overlappingcontainer$.style.display = (!data || !data.mods || data.mods.length === 0) ? 'none' : '';

        let tbody$ = document.querySelector('#overlappingcontainer table tbody');
        while(tbody$.firstChild) tbody$.removeChild(tbody$.firstChild);
        
        data.mods.forEach(e => {
            tbody$.appendChild(document.createElement('tr', {is: 'word-count'})).setData([e.item.id,e.item.start,e.item.end,overlapactionsselection(e.item.id, e.res)]);
        });
    }

    function queryForConflicts() {
        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        const startDate = s$.datepicker('getDate');
        if (!startDate) {
            spinner$.style.display = 'none';
            return;
        } else {
            spinner$.style.display = '';
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
                //spinner$.hide();
                spinner$.style.display = 'none';
            });
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
    part$.on('change', queryForConflicts);
    kind$.on('change', queryForConflicts);
    desc$.on('change', queryForConflicts);

})(jQuery)
