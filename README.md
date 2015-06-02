# ekloges_dieuthinton
Γεννήτρια Καταλόγου Εκλογέων Επιλογής Διευθυντών

## Εγκατάσταση

Κατεβάστε τον κώδικα :

```
$ git clone https://github.com/dideher/ekloges_dieuthinton.git
```

Δημιουργήστε το `virtualenv` της Python

```
$ cd ekloges_dieuthinton
$ virtualenv v
$ source v/bin/activate
$ pip install -U -r requirements.txt
```

Δοκιμάστε :

```
$ ./ekloges.py -h
usage: ekloges.py [-h] -r8 REPORT8 [--schoolId SCHOOLID]

optional arguments:
  -h, --help            show this help message and exit
  -r8 REPORT8, --report8 REPORT8
  --schoolId SCHOOLID   generate report for the given school id
```
