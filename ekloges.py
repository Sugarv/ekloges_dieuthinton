#!/usr/bin/python
#  -*- coding: utf-8 -*-

import csv
import codecs
import re
import argparse
import os
from prettytable import PrettyTable


report08_schools = {}
report08_employees = {}
report08_school_employees = {}


report16_employee = None
# The following (combined with report16_absence_reasons) is used when an employee is absent, has multiple assignments and not all schools have input this absence 
report16_absents = {}

# we will store employee school exclusion in the employee_school_exclusions dict
# format: key -> employee afm

employee_school_exclusions = {}

# school exclusions
excluced_schools = list()

# employee exclusions
excluced_employees = dict()



def filterAFM(rawAFM):
    return re.search('=\"(\d*)\"', rawAFM).group(1)

def csv_unireader(f, encoding="utf-8"):
    for row in csv.reader(codecs.iterencode(codecs.iterdecode(f, encoding), "utf-8"), delimiter=';', quotechar='"'):
        yield [e.decode("utf-8") for e in row]

def parseEmployeeExclusionList(reportPath):
    """
    Parses a CSV which in the first column contains the IDs of all employees that need to be excluded from
    processing
    :param reportPath:
    :return: a list of schools ids to exclude
    """
    result = dict()
    with open(reportPath, 'rb') as report_csvfile:
        reader = csv_unireader(report_csvfile, encoding='iso8859-7')
        for row in reader:
            afm = str(row[0])
            afm = afm if len(afm)==9 else '0'+afm
            result[afm]=(row[1] if len(row)>1 and row[1] != u'' else u'Άγνωστος λόγος εξαίρεσεις')


    return result

def parseSchoolExclusionList(reportPath):
    """
    Parses a CSV which in the first column contains the IDs of all schools that need to be excluded from
    processing
    :param reportPath:
    :return: a list of schools ids to exclude
    """
    result = list()
    with open(reportPath, 'rb') as report_csvfile:
        reader = csv_unireader(report_csvfile, encoding='iso8859-7')
        for row in reader:
            result.append(row[0])

    return result

def parseReport16(reportPath='/Users/slavikos/Downloads/CSV_2015-06-03-100905.csv'):
    """
    Parse report 16 (Κατάλογος Εκπαιδευτικών που Απουσιάζουν από Σχολικές Μονάδες)
    :param reportPath:
    :return:
    """

    report16_absence_reasons = [u'ΜΑΚΡΟΧΡΟΝΙΑ ΑΔΕΙΑ (>10 ημέρες)',u'ΑΠΟΣΠΑΣΗ ΣΤΟ ΕΞΩΤΕΡΙΚΟ',u'ΑΠΟΣΠΑΣΗ ΣΕ ΦΟΡΕΑ ΥΠ. ΠΑΙΔΕΙΑΣ',u'ΑΠΟΣΠΑΣΗ ΣΕ ΑΛΛΟ ΠΥΣΠΕ / ΠΥΣΔΕ',u'ΑΠΟΣΠΑΣΗ ΣΕ ΦΟΡΕΑ ΕΚΤΟΣ ΥΠ. ΠΑΙΔΕΙΑΣ',u'ΟΛΙΚΗ ΔΙΑΘΕΣΗ ΣΕ ΑΠΟΚΕΝΤΡΩΜΕΝΕΣ ΥΠΗΡΕΣΙΕΣ ΥΠ. ΠΑΙΔΕΙΑΣ']
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
            result[filterAFM(row[12])] = { "schoolId": row[6], "reason": "%s (%s)" % (row[22], row[23]) }
            
	    # check if generally absent (in case of multiple assignments) and insert in report16_absents
	    if row[24] in report16_absence_reasons or unicode(row[24]).startswith(u'ΜΑΚΡΟΧΡΟΝΙΑ ΑΔΕΙΑ (>10 ημέρες)'):
		    report16_absents[filterAFM(row[12])] = row[24]

    return result

def parseReport08(reportPath='/Users/slavikos/Downloads/CSV_2015-06-02-130003.csv'):
    excluded_school_types = [u'Νηπιαγωγεία']

    with open(reportPath, 'rb') as report08_csvfile:
        spamreader = csv_unireader(report08_csvfile, encoding='iso8859-7')
        firstRow = True
        for row in spamreader:

            if firstRow:
                firstRow = False
                continue
            #exclude some school types
            if row[4] in excluded_school_types:
                continue

            # check if the school id is excluded
            if row[6] in excluced_schools:
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
                'hours': int(row[44]) if row[44] else 0, # Ώρες Υποχ. Διδακτικού Ωραρίου Υπηρέτησης στο Φορέα
                'teachingHours': (int(row[46]) if row[46] else 0) + (int(row[47]) if row[47] else 0),
            }

            employeeObj['assigments'].append(assigmentObj)

            # report08_school_employees[schoolObj['id']].append(assigmentObj)


def isExcluded(employeeAfm, schoolId):
    """
    Determines if an employee is excluded from school unit id. If the schoolId is None, then
    the operation will check the general exclusion list. The operation will
    return None if the employee is not excluded or a description if the employee
    should be excluded
    :param employeeAfm: The employee's AFM
    :type employeeAfm: str
    :param schoolId: The school ID to check for exclusion
    :type schoolId: str
    :return: None if the employee is not excluded or a description if the employee should be excluded
    """
    if schoolId is None:
        return excluced_employees.get(employeeAfm, None)

    if len(employee_school_exclusions) > 0:
        exclusion = employee_school_exclusions.get(employeeAfm, None)
        if exclusion:
            # employee is probably excluded
            if exclusion.get('schoolId', '') == schoolId:
                return exclusion.get('reason', u"Άγνωστος λόγος εξαίρεσεις")
            else:
                return None
        else:
            return None
    else:
        return None


def processSchool(id, filter0=False):

    schoolObj = report08_schools.get(id, None)
    acceptedList = list()
    rejectedList = list()

    # fetch school employees, if school is not excluded
    schoolEmployees = schoolObj.get('employees', list()) if id not in excluced_schools else list()
    for employee in schoolEmployees:

        # check if the employee is in the general exclusion list
        excludedReason = isExcluded(employeeAfm=employee['afm'], schoolId=None)

        # check if the employee is in the exclusion list (for the given school)
        if excludedReason is None:
            excludedReason = isExcluded(employeeAfm=employee['afm'], schoolId=schoolObj['id'])

        if excludedReason:
            # employee has been excluded
            rejectedList.append(
                {
                    'employee': employee,
                    'excludedReason': excludedReason,
                }
            )
            continue

        if report16_absents and employee['afm'] in report16_absents:
        # exclude report16_absents from all schools (if they have more than one assignments)
            continue

        # some (in our case pe05, pe07) employees may have multiple secondary assignments with equal, more than the main, hours
        # if this happens, select and enroll them in their main assignment school (as instructed by the ministry of education)
        foundAssigment = None
        mainAssigment = None
        mainAssigmentHours = None
        assigmentHours = list()
        if len(employee['assigments']) > 2:
            for assigment in employee['assigments']:
                if assigment['assigment'] == u'Από Διάθεση ΠΥΣΠΕ/ΠΥΣΔΕ':
                    mainAssigment = assigment
                    mainAssigmentHours = assigment['hours']
                    continue
                else:
                    assigmentHours.append (assigment['hours'])
                    continue
            maxHours = max(assigmentHours)
            if assigmentHours.count(maxHours)>1:
                foundAssigment = mainAssigment
        # end of multi max assignments


        primaryAssignemtns = [ u'Από Διάθεση ΠΥΣΠΕ/ΠΥΣΔΕ', u'Απόσπαση (με αίτηση - κύριος φορέας)', u'Οργανικά', u'Οργανικά από Άρση Υπεραριθμίας' ]

        selectedAssigment = None

        for assigment in employee['assigments']:
            if foundAssigment:
                selectedAssigment = foundAssigment
                break

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
               	if assigment['assigment'] in primaryAssignemtns:
                    selectedAssigment = assigment

                else:
                    pass

        # we've checked all assignments and we have the selected assignment
        # in the selectedAssigment variable. Check if the assignment references
        # the current school and the hours attribute is > 0
        if selectedAssigment['schoolId'] == id and selectedAssigment['hours'] > 0:

            if filter0 and selectedAssigment['teachingHours'] == 0:
                # we've been asked to filter out employees with assignments
                # in the current school but without teaching hours
                rejectedList.append({
                    'employee': employee,
                    'excludedReason': u"Αποκλεισμός λόγο μη ανάθεσης διδακτικού έργου στην μονάδα",
                })
                continue

            # woooo! we have a winner !
            acceptedList.append(
                {
                    'employee': employee,
                    'assigment': selectedAssigment,
                }
            )
        else:
            # ok, employee is rejected
            schName = report08_schools.get(selectedAssigment['schoolId'], None)['title']
            rejectedList.append(
                {
                    'employee': employee,
                    'excludedReason': u"Τοποθετημένος για '%s' ώρες στην μονάδα '%s' (%s)\n με σχέση '%s'(Σχ.Έργ.: '%s')" % (selectedAssigment['hours'], selectedAssigment['schoolId'], schName, selectedAssigment['assigment'], selectedAssigment['type']),
                }
            )

    return {
        'school' : schoolObj,
        'accepted': sorted(acceptedList, key=lambda employee: employee['employee']['surname']),
        'rejected': sorted(rejectedList, key=lambda employee: employee['employee']['surname']),
    }

def writeReportToFile(reportName, resultStr, basePath='/tmp', encoding="utf-8"):
    filePath = os.path.join(basePath, reportName)
    with codecs.open(filePath, mode="w", encoding=encoding) as textFile:
        textFile.write(resultStr)
    return filePath

def replace_all(text, dic):
    for i, j in dic.iteritems():
        text = text.replace(i, j)
    return text
    
def shortenTitle(schName):
    shortenDic = {u'ΟΛΟΗΜΕΡΟ' : u'ΟΛ', u'ΔΗΜΟΤΙΚΟ' : u'Δ.', u'ΣΧΟΛΕΙΟ' : u'Σ.', u'/' : ''}
    return replace_all(schName, shortenDic)

def printTabularResults(result, includeRejected=False):

    schoolObj = result.get('school', dict())

    resultString = "\n"
    resultString = resultString + "::::::::::::::::::::::::::::::::::::::::::::::::\n"
    resultString = resultString + ":: %s - (%s) ::\n" % (schoolObj['title'], schoolObj['id'])
    resultString = resultString + "::::::::::::::::::::::::::::::::::::::::::::::::\n"
    resultString = resultString + "\n\n"


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
    for r in result.get('accepted', list()):
        e = r['employee']
        a = r['assigment']
        x.add_row([counter, e['id'], e['afm'], e['surname'], e['name'], e['fatherName'], e['specialization'], a['type'], a['assigment'], a['hours'], a['teachingHours']])
        counter = counter + 1

    resultString = resultString + x.get_string()

    if includeRejected:
        x = PrettyTable(["#","ΑΜ", "ΑΦΜ", u"ΕΠΩΝΥΜΟ", u"ΟΝΟΜΑ", u"ΠΑΤΡΩΝΥΜΟ", u"ΕΙΔΙΚΟΤΗΤΑ", u"ΑΠΟΚΛΕΙΣΜΟΣ ΑΠΟ ΨΗΦΟΦΟΡΙΑ"])
        x.align[u"#"] = "l"
        x.align[u"ΕΠΩΝΥΜΟ"] = "r"
        x.align[u"ΟΝΟΜΑ"] = "r"
        x.align[u"ΠΑΤΡΩΝΥΜΟ"] = "r"
        x.align[u"ΕΙΔΙΚΟΤΗΤΑ"] = "r"
        x.align[u"ΑΠΟΚΛΕΙΣΜΟΣ ΑΠΟ ΨΗΦΟΦΟΡΙΑ"] = "l"

        counter = 1
        for r in result.get('rejected', list()):
            e = r['employee']
            x.add_row([counter, e['id'], e['afm'], e['surname'], e['name'], e['fatherName'], e['specialization'], r['excludedReason'] ])
            counter = counter + 1

        resultString = resultString + "\n\n"
        resultString = resultString + u"###############################\n"
        resultString = resultString + u"##### Λίστα Αποκλεισμένων #####\n"
        resultString = resultString + u"###############################\n"
        resultString = resultString + "\n\n"
        resultString = resultString + x.get_string()

    return resultString

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('-r8', "--report8", help="path to myschool report 8", required=True, type=str)
    parser.add_argument('-r16', "--report16", help="path to myschool report 16", type=str)
    parser.add_argument('-se', "--schoolExclusion", help="path to school exclusion list", type=str)
    parser.add_argument('-ee', "--employeeExclusion", help="path to school exclusion list", type=str)
    parser.add_argument('--schoolId', type=str, help='generate report for the given school id')
    parser.add_argument('--filter0', action='store_true', default=False, help='filter employees without teaching hour(s)')
    parser.add_argument('--rejected', action='store_true', default=False, help='print rejected employees in results')
    parser.add_argument('--outputDir', type=str, help='the base path where output files should be placed')
    parser.add_argument('--titleFiles', action='store_true', default=False, help='output school titles as filenames')
    parser.add_argument('--outputEncoding',  default='utf-8', help='set output encdoding')


    args = parser.parse_args()

    if args.schoolExclusion:
        # path to school exclusion has been specified, so go and parse
        excluced_schools = parseSchoolExclusionList(reportPath=args.schoolExclusion)

    if args.employeeExclusion:
        excluced_employees = parseEmployeeExclusionList(reportPath=args.employeeExclusion)

    # parse report 08 as it is mandatory !
    parseReport08(reportPath=args.report8)

    if args.report16:
        # path to report 16 has been specified, so parse!
        employee_school_exclusions.update(parseReport16(reportPath=args.report16))

    if args.schoolId:
        schoolObj = report08_schools[args.schoolId]
        result = processSchool(id=args.schoolId, filter0=args.filter0)
        r = printTabularResults(result, includeRejected=args.rejected)
        if args.outputDir:
            outputFileName = shortenTitle(schoolObj['title']) if args.titleFiles else args.schoolId
            path = writeReportToFile(reportName=("%s.txt" % outputFileName), resultStr=r, basePath=args.outputDir, encoding=args.outputEncoding)
            print "[*] School '%s' (%s) report has been written to file '%s'" % (args.schoolId,schoolObj['title'], path)
        else:
            print r
        exit()

    for school in report08_schools:
        schoolObj = report08_schools[school]
        result = processSchool(id=school, filter0=args.filter0)
        r = printTabularResults(result, includeRejected=args.rejected)
        if args.outputDir:
            outputFileName = shortenTitle(schoolObj['title']) if args.titleFiles else school
            path = writeReportToFile(reportName=("%s.txt" % outputFileName), resultStr=r, basePath=args.outputDir, encoding=args.outputEncoding)
            print "[*] School '%s' (%s) report has been written to file '%s'" % (school,schoolObj['title'], path)
        else:
            print r

