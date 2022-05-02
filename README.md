Survtur Glacier
===============

GUI client for with [Amazon Glacier](https://aws.amazon.com/s3/storage-classes/glacier/) — cheap and very cold data storage.
Archive naming is compatible with [FastGlacier for Windows](https://fastglacier.com). Written on Python and Qt.

![Main window example](./.readme_images/main_window.png)

Can do
------
* List vaults content.
* Upload archives.
* Download archives.
* Emulate directory structure.
* Check for duplicates before uploading.


Can't do
--------
* [Create/delete vaults](https://docs.aws.amazon.com/amazonglacier/latest/dev/working-with-vaults.html)
* Delete archives (planned).

Installation
------------
    pip3 install survtur-glacier

Starting
-------
After installation on most systems this command should work:

    survtur-glacier    

If you see command not found error, try this:
    
    python3 -c "import survtur_glacier as s; s.start()"

First start and AWS credentials
-------------------------------
On first start app will create `~/.survtur-glacier/config.ini`.
You should write there your AWS credentials and region.

Without correct credentials, app will not start. You'll see error in terminal.


Cancelling and removing faulty tasks
------------------------------------

Whe you cancel task, it goes to "Faulty" list of tasks. All faulty tasks will be restarted on next programm start.
If you want to completely remove faulty and cancelled tasks, you have to delete faulty tasks.

To clean cancelled tasks:
   1. Go to faulty task list.
   2. Select tasks you want to delete.
   3. Click Right mouse button and choose "Delete" 
