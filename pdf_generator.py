"""
Generador de PDF - Reporte ISTQB Foundation Level
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
from xml.sax.saxutils import escape

# Helvetica/Courier no renderizan emojis: los traducimos a marcadores ASCII.
_EMOJI_MAP = {
    "🔧": "[tool]", "✓": "[ok]", "✗": "[x]", "⚠": "[!]",
    "🟢": "[ok]", "🔴": "[x]", "🟠": "[!]", "🟡": "[~]", "⚪": "[-]",
}


def _clean_log(line: str) -> str:
    """Escapa caracteres XML y reemplaza emojis para que el PDF no muestre cajas."""
    for emoji, repl in _EMOJI_MAP.items():
        line = line.replace(emoji, repl)
    # Quita cualquier otro caracter no-latino que Courier no pueda dibujar.
    line = "".join(c if ord(c) < 0x2500 else "?" for c in line)
    return escape(line)


class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._define_custom_styles()
    
    def _define_custom_styles(self):
        """Define estilos personalizados para Greensoft"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#00ff99'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='BugTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#00ff99'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            fontSize=11,
            textColor=colors.HexColor('#00ff99'),
            fontName='Helvetica-Bold',
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=10,
            alignment=TA_JUSTIFY
        ))

        self.styles.add(ParagraphStyle(
            name='TableCell',
            fontSize=8,
            textColor=colors.black,
            leading=10
        ))

        self.styles.add(ParagraphStyle(
            name='CellLabel',
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            leading=12
        ))

        self.styles.add(ParagraphStyle(
            name='CellValue',
            fontSize=9,
            textColor=colors.black,
            leading=12
        ))

        self.styles.add(ParagraphStyle(
            name='SessionValue',
            fontSize=10,
            textColor=colors.black,
            leading=13,
            wordWrap='CJK'  # corta URLs/tokens largos sin espacios
        ))

        self.styles.add(ParagraphStyle(
            name='BugHeaderCell',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=12
        ))

        self.styles.add(ParagraphStyle(
            name='LogLine',
            fontName='Courier',
            fontSize=7,
            leading=9,
            textColor=colors.black,
            wordWrap='CJK'  # corta líneas de log muy largas
        ))
    
    def generate_pdf(self, filename: str, session_id: str, target_url: str,
                     mode: str, bugs: list, test_cases: list = None, logs: list = None):
        """Genera PDF con reporte ISTQB"""
        test_cases = test_cases or []
        logs = logs or []
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Header
        story.append(Paragraph(
            "📋 REPORTE DE DEFECTOS - ISTQB",
            self.styles['CustomTitle']
        ))
        
        # Información de sesión
        sv = self.styles['SessionValue']
        session_data = [
            ['Proyecto:', Paragraph('GREENSOFT Testing Framework', sv)],
            ['URL Testeada:', Paragraph(target_url, sv)],
            ['Session ID:', Paragraph(session_id, sv)],
            ['Modo:', Paragraph(mode.upper(), sv)],
            ['Entorno:', Paragraph('Análisis vía HTTP (sin navegador)', sv)],
            ['Reportado por:', Paragraph('GREENSOFT Testing Framework', sv)],
            ['Fecha:', Paragraph(datetime.now().strftime('%d/%m/%Y %H:%M:%S'), sv)]
        ]
        
        session_table = Table(session_data, colWidths=[2*inch, 4*inch])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#00ff99')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(session_table)
        story.append(Spacer(1, 20))
        
        # Resumen
        story.append(Paragraph("RESUMEN EJECUTIVO", self.styles['BugTitle']))
        
        critical = sum(1 for b in bugs if b.get('severity') == 'CRITICAL')
        high = sum(1 for b in bugs if b.get('severity') == 'HIGH')
        medium = sum(1 for b in bugs if b.get('severity') == 'MEDIUM')
        low = sum(1 for b in bugs if b.get('severity') == 'LOW')
        
        summary_data = [
            ['Total Bugs', 'Critical', 'High', 'Medium', 'Low'],
            [str(len(bugs)), str(critical), str(high), str(medium), str(low)]
        ]
        
        summary_table = Table(summary_data, colWidths=[1.2*inch]*5)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00ff99')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Bugs
        story.append(Paragraph("BUGS ENCONTRADOS", self.styles['BugTitle']))
        story.append(Spacer(1, 12))
        
        for i, bug in enumerate(bugs, 1):
            severity = bug.get('severity', 'MEDIUM')
            color_map = {
                'CRITICAL': colors.HexColor('#ff1744'),
                'HIGH': colors.HexColor('#ff6d00'),
                'MEDIUM': colors.HexColor('#ffc400'),
                'LOW': colors.HexColor('#00c853')
            }
            
            bug_color = color_map.get(severity, colors.grey)
            
            # Encabezado del bug (título envuelto para que ajuste)
            hdr = self.styles['BugHeaderCell']
            bug_header_data = [
                [Paragraph(f"BUG {i}", hdr), Paragraph(bug.get('title', 'Sin título'), hdr),
                 Paragraph(severity, hdr)]
            ]
            bug_header_table = Table(bug_header_data, colWidths=[0.8*inch, 3.8*inch, 1.2*inch])
            bug_header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), bug_color),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ]))
            story.append(bug_header_table)

            # Detalle del bug (celdas envueltas: ya no se desbordan)
            lbl, val = self.styles['CellLabel'], self.styles['CellValue']
            detail_rows = [
                ('DESCRIPCIÓN:', bug.get('description', '')),
                ('RESULTADO ESPERADO:', bug.get('expected', '')),
                ('RESULTADO ACTUAL:', bug.get('actual', '')),
                ('IMPACTO:', bug.get('impact', '')),
            ]
            if bug.get('steps'):
                detail_rows.append(('PASOS PARA REPRODUCIR:', '<br/>'.join(bug.get('steps', []))))
            if bug.get('services'):
                detail_rows.append(('SERVICIOS:', ', '.join(bug.get('services', []))))

            bug_details = [[Paragraph(k, lbl), Paragraph(v, val)] for k, v in detail_rows]
            detail_table = Table(bug_details, colWidths=[1.6*inch, 4.2*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(detail_table)
            story.append(Spacer(1, 15))
        
        # Casos de prueba
        if test_cases:
            story.append(Spacer(1, 20))
            story.append(Paragraph("CASOS DE PRUEBA", self.styles['BugTitle']))
            story.append(Spacer(1, 12))

            cell = self.styles['TableCell']
            tc_header = ['ID', 'Descripción', 'Resultado esperado', 'Status']
            tc_rows = [tc_header]
            for tc in test_cases:
                tc_rows.append([
                    Paragraph(tc.get('id', ''), cell),
                    Paragraph(tc.get('description', ''), cell),
                    Paragraph(tc.get('expected', ''), cell),
                    Paragraph(tc.get('status', ''), cell),
                ])
            tc_table = Table(tc_rows, colWidths=[0.9*inch, 2.6*inch, 2.0*inch, 0.8*inch])
            tc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00ff99')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(tc_table)

        # Logs de ejecución (reales)
        if logs:
            story.append(Spacer(1, 20))
            story.append(Paragraph("LOGS DE EJECUCIÓN", self.styles['BugTitle']))
            story.append(Spacer(1, 8))
            log_rows = [[Paragraph(_clean_log(l), self.styles['LogLine'])] for l in logs]
            log_table = Table(log_rows, colWidths=[6.2*inch])
            log_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(log_table)

        # Footer
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            "Reporte generado automáticamente por GREENSOFT Testing Framework - ISTQB Foundation Level",
            self.styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
