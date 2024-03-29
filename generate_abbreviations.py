"""
Title: Abbreviation generator for project paths on VU storage
Author: Brett G. Olivier
version: 0.8-alpha

Usage (Collab): https://colab.research.google.com/drive/1ikMDIBbPMxIkiMj8MnWLTmPEgs29a66F?usp=sharing 
Usage (Local): python3 generate_abbreviations.py

Requires: openpyxl (pip install openpyxl)

(C) Brett G. Olivier, VU Amsterdam, 2022. Licenced for use under the BSD 3 clause

# Data needs to be loaded from Peter's org data file (default)

`data_input_name = 'pure_ou.json'`

"""

import os, json, pprint, openpyxl

def get_data(data_input_name, cDir, expressions):
    with open(os.path.join(cDir, data_input_name), 'r') as F:
        orgdata = json.load(F)
    
    # get list of existing abbreviations, if it exists
    if os.path.exists(os.path.join(cDir, '_abbr_list_previous.json')):
        with open(os.path.join(cDir, '_abbr_list_previous.json'), 'r') as F:
            prev_abbr_list = tuple(json.load(F))
    else:
        prev_abbr_list = ()

    # get list of obsolete terms, if it exists
    if os.path.exists(os.path.join(cDir, '_abbr_list_obsolete.json')):
        with open(os.path.join(cDir, '_abbr_list_obsolete.json'), 'r') as F:
            obsolete_terms = list(json.load(F))
    else:
        obsolete_terms = []

    output_data = {'Acronymns': []}
    for exp in expressions:
        output_data[exp] = {}

    return orgdata, output_data, prev_abbr_list, obsolete_terms


def check_for_obsolete(output_data, prev_abbr_list, obsolete_terms):
    acronew = [a.lower() for a in sorted(output_data['Acronymns'])]
    output_data['Obsolete_terms'] = obsolete_terms
    for acr in prev_abbr_list:
        if acr not in acronew:
            obsolete_terms.append(acr)
            output_data['Obsolete_terms'].append(acr)
    # this is a hack to get rid of term duplications which can probably be better sorted out above
    obsolete_terms = list(set(obsolete_terms))
    output_data['Obsolete_terms'] = list(set(output_data['Obsolete_terms']))
    return obsolete_terms


def make_acronymns(branch, out, expr, key, acro_repl, key_ignore, prev_abbr_list, obsolete_terms, faculty_repl_set, faculty_prefix):
    for e in branch:
        if branch[key] == 'Faculty':
            faculty_prefix = faculty_repl_set[branch['name']]
            #print(faculty_prefix)  
        
        if branch['name'] not in key_ignore and e == key and branch[key] in expr:
            acro = f'{faculty_prefix}-{acronize(branch["name"], acro_repl)}'
            if acro in out['Acronymns'] or acro.lower() in obsolete_terms:
                if acro.lower() in obsolete_terms:
                    print('Avoiding duplication of existing obsolete term: ', acro.lower())
                else:
                    print('Duplicate acronym: ', acro.lower())
                #out['Acronymns'].insert(0, (acro, branch['name']))
                acro = f'{faculty_prefix}-{acronize(branch["name"], acro_repl, duplicate=True)}'
            if acro.lower() not in prev_abbr_list:
                print('New Acronymn add:', acro.lower())
            else:
                print('Acronymn already exists:', acro.lower())
            out['Acronymns'].append(acro)
            out[branch[key]][branch['name']] = acro
        elif e == 'children':
            for c in branch['children']:
                make_acronymns(c, out, expr, key, acro_repl, key_ignore, prev_abbr_list, obsolete_terms, faculty_repl_set, faculty_prefix)
    for fac in out['Faculty']:
        out['Faculty'][fac] = out['Faculty'][fac].split('-')[0]


def acronize(words, replacements, duplicate=False):
    # single word names treated as Acronymns, shorten if needed.
    # words0 = words

    # clean phrase
    for r in replacements:
        words = words.replace(r, replacements[r])

    if len(words.split()) == 1:
        if not duplicate:
            words = words.upper()
        else:
            print('\nWARNING: not sure what to do with a duplicate single name:', words)
            raise(RuntimeWarning(), words)
    else:
        if not duplicate:
            words = ''.join(w[0] for w in words.split())
        else:
            # words = words.replace('and', ' ')
            words = ''.join(w[:2].upper() for w in words.split())

    # print(words0, ' --> ', words)
    return words


def write_data(output_file_name, output_path, output_data, expressions, output_lowercase):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_file_name = os.path.join(output_path, output_file_name)
        
    if output_lowercase:
        # first we lowercase all acronyms
        output_data['Acronymns'] = [a.lower() for a in sorted(output_data['Acronymns'])]
        for expr in expressions:
            for k in output_data[expr]:
                output_data[expr][k] = output_data[expr][k].lower()

    # dumps the entire output dataset
    with open(output_file_name + '-full.json', 'w') as F:
        json.dump(output_data, F, indent=' ')
        
    # store the last list of abbreviations to detect new ones in each run
    with open('_abbr_list_previous.json','w') as F:
        json.dump([a.lower() for a in sorted(output_data['Acronymns'])], F)


    # store the last list of obsolete terms to detect new ones in each run
    with open('_abbr_list_obsolete.json','w') as F:
        json.dump(sorted(output_data['Obsolete_terms']), F)

    # for the servicenow form.
    # seems easier to have a fixed name to quickly see if anything changed
    with open(os.path.join(output_path, 'servicenow-list.txt'), 'w') as F:
        for expr in expressions:
            if expr == 'Faculty':
                continue
            #F.write(f'# {expr}\n')
            # sort by abbreviation, in this case the value
            for dep in sorted(output_data[expr].items(), key=lambda x:x[1]):
                F.write(f'{dep[1]} | {dep[0]}')
                if dep[1] in output_data['Obsolete_terms']:
                    F.write(f'*')
                F.write(f'\n')

    # create an XLS workbook to record results over time, saved as sheets 
    xls_filename = os.path.join(output_path, '_abbreviation_history.xlsx')
    if not os.path.exists(xls_filename):
        xls = openpyxl.Workbook()
    else:
        xls = openpyxl.load_workbook(filename = xls_filename)

    # setup current worksheet
    act_sheet = xls.create_sheet(title = os.path.split(output_file_name)[-1])
    act_sheet.page_setup.fitToWidth = 1

    
    faculty_cntr = 2
    inst_cntr = 2
    dept_cntr = 2
    obsolete_cntr = 2
    col_map = {'Faculty' : 5,
               'Research Institute' : 3,
               'Department' : 1,
               'Obsolete_terms' : 7}
    
    cells = [] 
    cells.append(act_sheet.cell(1, 1, 'Dept. abbr.'))
    cells.append(act_sheet.cell(1, 2,'Department'))
    cells.append(act_sheet.cell(1, 3, 'Inst. abbr.'))
    cells.append(act_sheet.cell(1, 4, 'Institute'))
    cells.append(act_sheet.cell(1, 5, 'Fac. abbr.'))
    cells.append(act_sheet.cell(1, 6, 'Faculty'))
    cells.append(act_sheet.cell(1, 7, 'Obsolete terms'))
    for c_ in cells:
        c_.font = openpyxl.styles.Font(bold=True)
        
    
    col_widths = [len(act_sheet['A1'].value), 
                  len(act_sheet['B1'].value), 
                  len(act_sheet['C1'].value),
                  len(act_sheet['D1'].value), 
                  len(act_sheet['E1'].value), 
                  len(act_sheet['F1'].value), 
                  len(act_sheet['G1'].value)]

    # write data and determine max col widths
    for expr in expressions:
        for dep in sorted(output_data[expr].keys()):
            if expr == 'Faculty':
                act_sheet.cell(faculty_cntr, col_map[expr]+1, dep)
                act_sheet.cell(faculty_cntr, col_map[expr], output_data[expr][dep])
                if len(output_data[expr][dep]) > col_widths[4]:
                    col_widths[4] = len(output_data[expr][dep])
                if len(dep) > col_widths[5]:
                    col_widths[5] = len(dep)
                faculty_cntr += 1
            elif expr == 'Department':
                act_sheet.cell(dept_cntr, col_map[expr]+1, dep)
                act_sheet.cell(dept_cntr, col_map[expr], output_data[expr][dep])
                if len(output_data[expr][dep]) > col_widths[0]:
                    col_widths[0] = len(output_data[expr][dep])
                if len(dep) > col_widths[1]:
                    col_widths[1] = len(dep)
                dept_cntr += 1
            elif expr == 'Research Institute':
                act_sheet.cell(inst_cntr, col_map[expr]+1, dep)
                act_sheet.cell(inst_cntr, col_map[expr], output_data[expr][dep])
                if len(output_data[expr][dep]) > col_widths[2]:
                    col_widths[2] = len(output_data[expr][dep])
                if len(dep) > col_widths[3]:
                    col_widths[3] = len(dep)                
                inst_cntr += 1
    
    # add obsolete terms        
    for obs in output_data['Obsolete_terms']:
        act_sheet.cell(obsolete_cntr, col_map['Obsolete_terms'], obs)
        obsolete_cntr += 1

    sheet_col_map  = {0 : 'A',
                1 : 'B',
                2 : 'C',
                3 : 'D',
                4 : 'E',
                5 : 'F',
                6 : 'G',
                }

    # reformat column widths    
    for col in range(len(col_widths)):
        act_sheet.column_dimensions[sheet_col_map[col]].width = col_widths[col]
                     
    xls.save(xls_filename)
    xls.close()

    return output_data


if __name__ == '__main__':
    import os, time
    from custom_replacements import custom_repl_set1 as custom_repl
    from custom_replacements import faculty_repl_set as faculty_repl_set
    from custom_replacements import custom_ignore_set1 as custom_ignr
    
    cDir = os.path.dirname(os.path.abspath(os.sys.argv[0]))

    # File IO names
    data_input_name = 'pure_ou.json'
    # to test obsolete_terms
    #data_input_name = 'pure_ou_two_deletions.json' 
    output_file_name = time.strftime('%y%m%d%H%M')
    output_path = os.path.join(cDir, 'output')
    

    # These need to be defined and passed into the module methods
    expressions = ['Department', 'Research Institute', 'Faculty']
    searchkey = 'term'

    # get and initialise
    orgdata, output_data, prev_abbr_list, obsolete_terms = get_data(data_input_name, cDir, expressions)
    

    # find and acronize
    make_acronymns(
        orgdata, output_data, expressions, searchkey, custom_repl, custom_ignr, prev_abbr_list, obsolete_terms, faculty_repl_set, 'vu'
    )

    # check for obsolete terms
    obsolete_terms_new = check_for_obsolete(output_data, prev_abbr_list, obsolete_terms)
    print("Need to so something with Obsolete_terms")
    print(obsolete_terms)
    print(obsolete_terms_new)
    #if len(obsolete_terms) > 0:
        #raise(RuntimeWarning)    

    # write data
    final_output_data = write_data(output_file_name, output_path, output_data, expressions, output_lowercase=True)
    
    #pprint.pprint(final_output_data)
    print('\nOutput written to: {}\\{}.*'.format(output_path, output_file_name))


