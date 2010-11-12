from xlwt import Workbook, easyxf, Utils, Formula

def export_events(events, out_file, user=None, encoding='utf-8'):
    book = Workbook(encoding=encoding)
    sheet1 = book.add_sheet('Events')
    style_head = easyxf('font: bold true; borders: bottom thin')
    sheet1.write(0,0,'Event', style_head)
    #sheet1.col(0).width = 256 * 10 #doesn't work
    #sheet1.col(0).width = 0x0d00 + 15 # doesn't work
    sheet1.write(0,1,'Date', style_head)
    sheet1.write(0,2,'Days', style_head)
    sheet1.write(0,3,'Hours', style_head)
    sheet1.write(0,4,'Description', style_head)
    
    row = 1
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
        else:
            sheet1.write(row, 2, '')
            hours = (event['end'] - event['start']).seconds / 3600.0
            sheet1.write(row, 3, hours)
        sheet1.write(row, 4, event['description'])
        
        row += 1
     
    style_bold = easyxf('font: bold true')
    days_cell_range = Utils.rowcol_pair_to_cellrange(row1=1, col1=2, row2=row - 1, col2=2)
    sheet1.write(row, 2, Formula('SUM(%s)' % days_cell_range), style_bold)

    days_cell_range = Utils.rowcol_pair_to_cellrange(row1=1, col1=3, row2=row - 1, col2=3)
    sheet1.write(row, 3, Formula('SUM(%s)' % days_cell_range), style_bold)
    
    book.save(out_file)
        
            
    
    
