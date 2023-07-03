from odoo import api, models
import locale
from odoo.exceptions import ValidationError


class VpasInvoice(models.AbstractModel):
    _name = 'report.vpas_invoice.vpas_invoice'
    _description = 'Factura de Grupo VPAS'

    @staticmethod
    def description_format(name):
        characters = "]"
        index = name.find(characters)
        if index != -1:
            description = name[index + 1:]
        else:
            description = name
        return description

    @staticmethod
    def address_format(partner_id):
        street = partner_id.street if partner_id.street else ''
        street2 = partner_id.street2 if partner_id.street2 else ''
        zip_code = partner_id.zip if partner_id.zip else ''
        city = partner_id.city if partner_id.city else ''
        state = partner_id.state_id.name if partner_id.state_id.name else ''
        country = partner_id.country_id.name if partner_id.country_id.name else ''
        address = street + ' ' + street2 + ' ' + city + ' ' + state + ' ' + zip_code + ' ' + country
        return address

    @api.model
    def _get_report_values(self, docids, data=None):
        print('funcion para obtener datos del cliente para el reporte')
        locale.setlocale(locale.LC_ALL, 'es_ES.utf8')
        docs = self.env['account.move'].browse(docids[0])

        subtotal = 0.0
        descuento = 0.0
        
        # amount_untaxed = 0.0
        # exempt_sum = 0.0
        # tax_base = 0.0
        percentage = ''
        # tax_iva = 0.0
        iva_withheld = 0.0
        amount_total = 0.0
        discount_sum = 0.0
        purchase_order = ''
        tax_porcentaje = 0

        lines = []

        for ili in docs.invoice_line_ids:
            if ili.display_type in ['product']:
                if ili.price_subtotal >= 0:
                    subtotal += ili.price_subtotal

                    # unit_price_without_tax = 0.0
                    for ti in ili.tax_ids:
                        # Calculo de descuento por lineas
                        # if ili.discount:
                        #     discount_sum += round(ili.price_unit * (ili.discount / 100), 2)
                        # else:
                        #     discount_sum += 0.0

                        if ti.x_tipoimpuesto == 'IVA':
                            tax_porcentaje = ti.amount
                            # unit_price_without_tax = round(ili.price_unit / ((100 + ti.amount) / 100), 2)
                            # tax_base += ili.price_subtotal
                            line_iva_id = docs.line_ids.search([('name', '=', ti.name), ('move_id', '=', docs.id)])
                            # tax_iva = abs(line_iva_id.amount_currency)
                            percentage = line_iva_id.name
                        # else:
                            # unit_price_without_tax = ili.price_unit

                        # if ti.x_tipoimpuesto == 'EXENTO':
                        #     exempt_sum += ili.price_subtotal
                        # if ti.x_tipoimpuesto == 'RIVA':
                        #     line_riva_id = docs.line_ids.search([('name', '=', ti.name), ('move_id', '=', docs.id)])
                        #     if docs.x_tipodoc == 'Nota de Crédito':
                        #         iva_withheld = line_riva_id.debit
                        #     else:
                        #         iva_withheld = line_riva_id.credit

                    # if ili.tax_ids[0].name == 'Exento':
                    #     code = '(E)'
                    # else:
                    #     code = '(G)'
                    # amount_untaxed += unit_price_without_tax



                    vals = {
                        'price_subtotal': locale.format_string(' % 10.2f', ili.price_subtotal, grouping=True),
                        'price_total': locale.format_string('%10.2f', ili.price_total, grouping=True),
                        'default_code': ili.product_id.default_code,
                        'name': self.description_format(ili.name),
                        'product_uom_id': ili.product_uom_id.name,
                        'quantity': locale.format_string('%10.2f', ili.quantity, grouping=True),
                        'price_unit': locale.format_string('%10.2f', ili.price_unit, grouping=True),
                        'display_type': ili.display_type,
                        'kilos': locale.format_string('%10.2f', (ili.product_id.x_Kilos *ili.quantity), grouping=True),
                    }
                    lines.append(vals)
                
                else:
                    descuento += ili.price_subtotal

            # if docs.invoice_origin:
            #     sale_order_id = self.env['sale.order'].search([('name', '=', docs.invoice_origin)])
            #     if sale_order_id:
            #         purchase_order = sale_order_id.x_ocompra

        # if docs.currency_id.name != 'VES':
        #     iva_withheld = iva_withheld / docs.x_tasa if docs.x_tasa != 0 else 0.0

        # amount_total = tax_iva + tax_base + exempt_sum

        tax_base = subtotal + descuento
        tax_iva = (tax_base * tax_porcentaje) / 100
        amount_total = tax_base + tax_iva

        untaxed_rate_amount = tax_base * docs.x_tasa
        iva_rate_amount = tax_iva * docs.x_tasa
        total_rate_amount = amount_total * docs.x_tasa

        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'data': data,
            'docs': docs,
            'address': self.address_format(docs.partner_id),
            # 'billing_address': self.address_format(docs.x_studio_direccin_de_envo) if docs.x_studio_direccin_de_envo else self.address_format(docs.partner_id),
            'billing_address': self.address_format(docs.partner_shipping_id),
            'subtotal': locale.format_string('%10.2f', subtotal, grouping=True),
            'descuento': locale.format_string('%10.2f', descuento, grouping=True),
            'tax_base': locale.format_string('%10.2f', tax_base, grouping=True),
            'tax_iva': locale.format_string('%10.2f', tax_iva, grouping=True),
            'amount_total': locale.format_string('%10.2f', amount_total, grouping=True),


            
            'amount_untaxed': locale.format_string('%10.2f', docs.amount_untaxed, grouping=True),
            'untaxed_rate_amount': locale.format_string('%10.2f', untaxed_rate_amount, grouping=True),
            
            
            'iva_rate_amount': locale.format_string('%10.2f', iva_rate_amount, grouping=True),
            'total_rate_amount': locale.format_string('%10.2f', total_rate_amount, grouping=True),
            'lines': lines,
            'porcentaje': tax_porcentaje,

        }
        return docargs