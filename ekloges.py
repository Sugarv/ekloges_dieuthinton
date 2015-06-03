#!/usr/bin/python
#  -*- coding: utf-8 -*-

import csv
import codecs
import re
import argparse
from prettytable import PrettyTable


report08_schools = {}
report08_employees = {}
report08_school_employees = {}

def filterAFM(rawAFM):
    return re.search('=\"(\d*)\"', rawAFM).group(1)

def csv_unireader(f, encoding="utf-8"):
    for row in csv.reader(codecs.iterencode(codecs.iterdecode(f, encoding), "utf-8"), delimiter=';', quotechar='"'):
        yield [e.decode("utf-8") for e in row]


def parseReport08(reportPath='/Users/slavikos/Downloads/CSV_2015-06-02-130003.csv'):
    with open(reportPath, 'rb') as report08_csvfile:
        spamreader = csv_unireader(report08_csvfile, encoding='cp1253')
        firstRow = True
        for row in spamreader:

            if firstRow:
                firstRow = False
                continue

            # get school object

            schoolObj = report08_schools.get(row[6], None)

            if not schoolObj:
                # first time we see that school
                schoolObj = {
                    'id': row[6],
                    'title': row[7],
                    'email': row[10],
                    'employees': list()
                }
                # add school to dict
                report08_schools[row[6]] = schoolObj


            # fetch employee from cache
            employeeObj = report08_employees.get(row[16], None)
            if not employeeObj:
                # first time we see that employee
                employeeObj = {
                    'id': row[15] if row[15] else '',
                    'afm': filterAFM(row[16]),
                    'name': row[18],
                    'surname': row[19],
                    'fatherName': row[20],
                    'specialization': row[28],
                    'assigments': list()
                }
                # add the employee in the dict
                report08_employees[employeeObj.get('id')] = employeeObj
                # add to the school as dict as well
                schoolObj['employees'].append(employeeObj)

            assigmentObj = {
                'schoolId': schoolObj['id'],
                'type': row[33],
                'assigment': row[34],
                'isMaster': True if row[35] == u'Ναι' else False,
                'hours': int(row[39]) if row[39] else 0, # Ώρες Υποχ. Διδακτικού Ωραρίου Υπηρέτησης στο Φορέα
                'teachingHours': (int(row[41]) if row[41] else 0) + (int(row[42]) if row[42] else 0),
            }

            employeeObj['assigments'].append(assigmentObj)

            # report08_school_employees[schoolObj['id']].append(assigmentObj)


def processSchool(id):
    # find all employees in school

    schoolObj = report08_schools.get(id, None)
    result = list()
    for employee in schoolObj.get('employees', list()):
        selectedAssigment = None

        for assigment in employee['assigments']:

            if not selectedAssigment:
                selectedAssigment = employee['assigments'][0]
                continue

            if assigment['hours'] > selectedAssigment['hours']:
                # found an assigment with more hours, check the
                # new assigment
                selectedAssigment = assigment
            elif assigment['hours'] == selectedAssigment['hours']:
                # same hours ... need more logic
                pass

        # we've checked all assignments and we have the selected assignment
        # in the selectedAssigment variable. Check if the assignment references
        # the current school and the hours attribute is > 0
        if selectedAssigment['schoolId'] == id and selectedAssigment['hours'] > 0:
            # woooo! we have a winner !
            result.append(
                {
                    'employee': employee,
                    'assigment': selectedAssigment,
                }
            )

    return result

def printSchoolHeader(schoolObj):
    print ""
    print "::::::"
    print ":: %s - (%s) ::" % (schoolObj['title'], schoolObj['id'])
    print "::::::"
    print ""

def printTabularResults(result):

    x = PrettyTable(["#","ΑΜ", "ΑΦΜ", u"ΕΠΩΝΥΜΟ", u"ΟΝΟΜΑ", u"ΠΑΤΡΩΝΥΜΟ", u"ΕΙΔΙΚΟΤΗΤΑ", u"ΣΧΕΣΗ ΕΡΓΑΣΙΑΣ", u"ΤΟΠΟΘΕΤΗΣΗ ΣΤΗΝ ΜΟΝΑΔΑ", u"ΩΡΑΡΙΟ", u"ΑΝΑΘΕΣΕΙΣ"])
    x.align[u"#"] = "l"
    x.align[u"ΕΠΩΝΥΜΟ"] = "r"
    x.align[u"ΟΝΟΜΑ"] = "r"
    x.align[u"ΠΑΤΡΩΝΥΜΟ"] = "r"
    x.align[u"ΕΙΔΙΚΟΤΗΤΑ"] = "r"
    x.align[u"ΣΧΕΣΗ ΕΡΓΑΣΙΑΣ"] = "r"
    x.align[u"ΤΟΠΟΘΕΤΗΣΗ ΣΤΗΝ ΜΟΝΑΔΑ"] = "r"
    x.align[u"ΩΡΑΡΙΟ"] = "r"
    x.align[u"ΑΝΑΘΕΣΕΙΣ"] = "r"

    counter = 1
    for r in result:
        e = r['employee']
        a = r['assigment']
        x.add_row([counter, e['id'], e['afm'], e['surname'], e['name'], e['fatherName'], e['specialization'], a['type'], a['assigment'], a['hours'], a['teachingHours']])
        counter = counter + 1


    print x


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('-r8', "--report8", required=True, type=str)
    parser.add_argument('--schoolId', type=str, help='generate report for the given school id')
    args = parser.parse_args()

    # parse report 08
    parseReport08(reportPath=args.report8)

    if args.schoolId:
        schoolObj = report08_schools[args.schoolId]
        printSchoolHeader(schoolObj)
        result = processSchool(id=args.schoolId)
        printTabularResults(result)
        exit()

    for school in report08_schools:
        schoolObj = report08_schools[school]
        printSchoolHeader(schoolObj)
        result = processSchool(id=school)
        printTabularResults(result)

