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


report16_employee = None
report16_absents = {}


def filterAFM(rawAFM):
    return re.search('=\"(\d*)\"', rawAFM).group(1)

def csv_unireader(f, encoding="utf-8"):
    for row in csv.reader(codecs.iterencode(codecs.iterdecode(f, encoding), "utf-8"), delimiter=';', quotechar='"'):
        yield [e.decode("utf-8") for e in row]

def parseReport16(reportPath='/Users/slavikos/Downloads/CSV_2015-06-03-100905.csv'):
    """
    Parse report 16 (Κατάλογος Εκπαιδευτικών που Απουσιάζουν από Σχολικές Μονάδες)
    :param reportPath:
    :return:
    """

    report16_absence_reasons = [u'ΜΑΚΡΟΧΡΟΝΙΑ ΑΔΕΙΑ (>10 ημέρες)',u'ΑΠΟΣΠΑΣΗ ΣΤΟ ΕΞΩΤΕΡΙΚΟ']
    result = {}

    with open(reportPath, 'rb') as report_csvfile:
        reader = csv_unireader(report_csvfile, encoding='iso8859-7')
        firstRow = True
        for row in reader:

            if firstRow:
                # first row contains
                firstRow = False
                continue

            # note that employee with employeeAfm is missing from school schoolId
            result[filterAFM(row[12])] = row[6]
	    # check if generally absent (in case of multiple assignments) and insert in report16_absents
	    if row[24] in report16_absence_reasons:
		report16_absents[filterAFM(row[12])] = row[24]

    return result

def parseReport08(reportPath='/Users/slavikos/Downloads/CSV_2015-06-02-130003.csv'):
    with open(reportPath, 'rb') as report08_csvfile:
        spamreader = csv_unireader(report08_csvfile, encoding='iso8859-7')
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
            employeeAfm = filterAFM(row[16])

            employeeObj = report08_employees.get(employeeAfm, None)

            if not employeeObj:
                # first time we see that employee
                employeeObj = {
                    'id': row[15] if row[15] else '',
                    'afm': employeeAfm,
                    'name': row[19],
                    'surname': row[18],
                    'fatherName': row[20],
                    'specialization': row[28],
                    'assigments': list()
                }
                # add the employee in the dict
                report08_employees[employeeObj.get('afm')] = employeeObj
                # add to the school as dict as well
                schoolObj['employees'].append(employeeObj)
            else:
                # employee exists in the report08_employee dict, so add it
                # (if he does not exist) in the schools dict as well
                if employeeObj not in schoolObj['employees']:
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


def processSchool(id, filter0=False):
    # find all employees in school

    schoolObj = report08_schools.get(id, None)
    result = list()
    for employee in schoolObj.get('employees', list()):

        # check if we have report16 data available
        if report16_employee and report16_employee.get(employee['afm']) == schoolObj['id']:
            # report 16 is available, check if the employee is excluded and the employee
            # has been reported missing in the school, so ignore
            continue

	if report16_absents and employee['afm'] in report16_absents:
	    # exclude report16_absents from all schools (if they have more than one assignments)
	    continue


        primaryAssignemtns = [ u'Από Διάθεση ΠΥΣΠΕ/ΠΥΣΔΕ', u'Απόσπαση (με αίτηση - κύριος φορέας)', u'Οργανικά', u'Οργανικά από Άρση Υπεραριθμίας' ]

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
                # deal with same hour assignments
                # selected assigment will be accepted if the type is a primary assignment
                if assigment['type'] in primaryAssignemtns:
                    selectedAssigment = assigment

		else:
		    selectedAssigment = assigment

        # we've checked all assignments and we have the selected assignment
        # in the selectedAssigment variable. Check if the assignment references
        # the current school and the hours attribute is > 0
        if selectedAssigment['schoolId'] == id and selectedAssigment['hours'] > 0:

            if filter0 and selectedAssigment['teachingHours'] == 0:
                # we've been asked to filter out employees with assignments
                # in the current school but without teaching hours
                continue

            # woooo! we have a winner !
            result.append(
                {
                    'employee': employee,
                    'assigment': selectedAssigment,
                }
            )

    return sorted(result, key=lambda employee: employee['employee']['surname'])

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

    parser.add_argument('-r8', "--report8", help="path to myschool report 8", required=True, type=str)
    parser.add_argument('-r16', "--report16", help="path to myschool report 16", type=str)
    parser.add_argument('--schoolId', type=str, help='generate report for the given school id')
    parser.add_argument('--filter0', action='store_true', default=False, help='filter employees without teaching hour(s)')
    args = parser.parse_args()

    # parse report 08 as it is mandatory !
    parseReport08(reportPath=args.report8)

    if args.report16:

        # path to report 16 has been specified, so parse!
        report16_employee = parseReport16(reportPath=args.report16)

    if args.schoolId:
        schoolObj = report08_schools[args.schoolId]
        printSchoolHeader(schoolObj)
        result = processSchool(id=args.schoolId, filter0=args.filter0)
        printTabularResults(result)
        exit()

    for school in report08_schools:
        schoolObj = report08_schools[school]
        printSchoolHeader(schoolObj)
        result = processSchool(id=school, filter0=args.filter0)
        printTabularResults(result)

