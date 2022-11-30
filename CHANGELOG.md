# Version 17.2

* JQuery Hierarchy Select for Bootstrap 4 (Orgunit-Filter)
* alle Mitarbeiter rekursiv ab selektierten Team
* "(besondere Situation)" entfernt

# Version 17

* Sticky header
* New: default value for Teamfilter (WEK-2094 / issue30)
* Change: Filterlayout 
* New: Pillow renderer
* Breaking: organizational unit assigned through external data
* Breaking: Readiness probe endpoint changed to `status/up`
* New: Python 3.10
* New: Django 4
* New: Health check endpoint `status/ht/`
* New: prometheus monitoring
* Change: Build docker image through github workflow action

# Version 16

* Filter index view with user names
* Python 3.9
* Health check endpoint
* New documentation with [mkdocs](https://www.mkdocs.org/) at https://erikwegner.github.io/wamytm/

# Version 15

Allow list views to be embedded

# Version 14

  * When creating a new time range entry, overlapping conflicts are detected and an action is proposed.
  * TravisCI build for test execution

# Version 13

  * Remove fields _kind_ and _data_ from admin [ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/)
  * Enable delegation: users can create time range entries for other users of assigned orgunits

# Version 12

  * Filter orgunit on index page

# Version 11 

  * Subkinds removed (for now)
  * Indexes
  * Dependencies updated

# Version 10 

  * Allow saving time range with kind detail
  * Allow saving time range with partial information
  * Allow saving time range with a description

# Version 9 

  * django-oauth-toolkit downgraded

# Version 8

  * Include OrgUnit in admin
  * Export week data to csv
  * Beta-Feature: iCal-Support

# Version 7 

 * Sort by names

# Version 6

 * Fix date comparison on view list1

# Version 5

  * [Datepicker](https://github.com/uxsolutions/bootstrap-datepicker) added
  * Front page: go to date

# Version 4

  * I18N

# Version 3

  * Release

# Version 2

  * Show first and last name when adding new time ranges
  * Show kind of time
  * Support all day events for holidays etc.
  * Support paging through week view

# Version 1

   * Initial release
