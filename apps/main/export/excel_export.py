from pprint import pprint
from collections import defaultdict
from xlwt import Workbook, easyxf, Utils, Formula

def export_events(events, out_file, user=None, encoding='utf-8'):
    book = Workbook(encoding=encoding)
    sheet1 = book.add_sheet('Events')
    style_head = easyxf('font: bold true; borders: bottom thin')
    style_italic = easyxf('font: italic true')
    style_bold = easyxf('font: bold true')
    sheet1.write(0,0,'Event', style_head)
    #sheet1.col(0).width = 256 * 10 #doesn't work
    #sheet1.col(0).width = 0x0d00 + 15 # doesn't work
    sheet1.write(0,1,'Date', style_head)
    sheet1.write(0,2,'Days', style_head)
    sheet1.write(0,3,'Hours', style_head)
    sheet1.write(0,4,'Description', style_head)
    
    row = 1
    days_spent = defaultdict(float)
    hours_spent = defaultdict(float)
    for event in events:
        sheet1.write(row, 0, event['title'])
        sheet1.write(row, 1, event['start'], easyxf(
          num_format_str='YYYY-MM-DD'
        ))
        #sheet1.row(row).write(1, event['start'])
        #sheet1.row(row).set_cell_date(1, event['start'])
        if event['all_day']:
            days = event['end'] - event['start']
            sheet1.write(row, 2, days.days + 1)
            sheet1.write(row, 3, '')
            for tag in event['tags']:
                days_spent[tag] += days.days + 1
            if not event['tags']:
                days_spent[''] += days.days + 1
        else:
            sheet1.write(row, 2, '')
            hours = (event['end'] - event['start']).seconds / 3600.0
            sheet1.write(row, 3, round(hours,1))
            for tag in event['tags']:
                hours_spent[tag] += hours
            if not event['tags']:
                hours_spent[''] += hours
        sheet1.write(row, 4, event['description'])
        
        row += 1
        
    if row > 1:
        style_bold = easyxf('font: bold true')
        days_cell_range = Utils.rowcol_pair_to_cellrange(row1=1, col1=2, row2=row - 1, col2=2)
        sheet1.write(row, 2, Formula('SUM(%s)' % days_cell_range), style_bold)
    
        days_cell_range = Utils.rowcol_pair_to_cellrange(row1=1, col1=3, row2=row - 1, col2=3)
        sheet1.write(row, 3, Formula('SUM(%s)' % days_cell_range), style_bold)
    
    
    ## Now write the summations by tags
    
    if '' in days_spent:
        days_spent['Untagged'] = days_spent.pop('')
    days_spent = days_spent.items()
    days_spent.sort(lambda x,y: cmp(y[1], x[1]))
    
    if '' in hours_spent:
        hours_spent['Untagged'] = hours_spent.pop('')
    hours_spent = hours_spent.items()
    hours_spent.sort(lambda x,y: cmp(y[1], x[1]))
    
    sheet2 = book.add_sheet('Report')
    sheet2.write(0,0,'Days', style_head)
    row = 1
    if days_spent:
        row += 1 
        sheet2.write(row,0, 'Tag', style_bold)
        sheet2.write(row,1, 'Days', style_bold)
        total = 0.0
        for tag, days in days_spent:
            row += 1
            if tag == 'Untagged':
                sheet2.write(row, 0, tag, style_italic)
            else:
                sheet2.write(row, 0, tag)
            sheet2.write(row, 1, days)
            total += days
        row += 1
        sheet2.write(row, 0, 'Total', style_bold)
        sheet2.write(row, 1, total, style_bold)
        row += 1
    if hours_spent:
        row += 1 
        sheet2.write(row,0, 'Tag', style_bold)
        sheet2.write(row,1, 'Hours', style_bold)
        total = 0.0
        for tag, hours in hours_spent:
            row += 1
            if tag == 'Untagged':
                sheet2.write(row, 0, tag, style_italic)
            else:
                sheet2.write(row, 0, tag)
            sheet2.write(row, 1, hours)
            total += hours
        row += 1
        sheet2.write(row, 0, 'Total', style_bold)
        sheet2.write(row, 1, total, style_bold)
        row += 1

    
    book.save(out_file)
        
            
    
    
