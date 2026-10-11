from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime

from accounts.models import CustomUser
from departments.models import Department
from employees.models import Employee
from payroll.models import SalaryStructure, PayrollRecord
from payroll.services import generate_payslip_pdf

class PayrollModuleTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Dev', code='DEV')
        self.user = CustomUser.objects.create_user(username='payroll_tester', role=CustomUser.Role.EMPLOYEE)
        self.emp = Employee.objects.create(
            employee_id='EMP-PAY-01',
            user=self.user,
            first_name='Bruce',
            last_name='Wayne',
            email='bruce@test.com',
            phone='+1 555-7777',
            department=self.dept,
            designation='Architect',
            basic_salary=Decimal('50000.00')
        )
        self.structure = SalaryStructure.objects.create(
            employee=self.emp,
            basic_salary=Decimal('50000.00'),
            hra=Decimal('20000.00'),
            transport_allowance=Decimal('2000.00'),
            medical_allowance=Decimal('1500.00'),
            special_allowance=Decimal('1000.00'),
            pf_rate_percent=Decimal('12.00'),
            professional_tax=Decimal('200.00')
        )

    def test_payroll_record_calculations(self):
        # Gross = 50000 + 20000 + 4500 = 74500
        # PF = 50000 * 0.12 = 6000
        # Tax = 200
        # Deductions = 6200
        # Net = 74500 - 6200 = 68300
        gross = Decimal('74500.00')
        pf = Decimal('6000.00')
        tax = Decimal('200.00')
        tot_ded = pf + tax
        net = gross - tot_ded

        record = PayrollRecord.objects.create(
            employee=self.emp,
            month=4,
            year=2026,
            basic_salary=Decimal('50000.00'),
            hra=Decimal('20000.00'),
            allowances_total=Decimal('4500.00'),
            bonus=Decimal('0.00'),
            gross_salary=gross,
            pf_deduction=pf,
            tax_deduction=tax,
            unpaid_leave_deduction=Decimal('0.00'),
            total_deductions=tot_ded,
            net_salary=net
        )
        self.assertEqual(record.net_salary, Decimal('68300.00'))
        self.assertTrue(record.payslip_number.startswith('PAY-202604-'))

    def test_generate_payslip_pdf_returns_valid_stream(self):
        record = PayrollRecord.objects.create(
            employee=self.emp,
            month=4,
            year=2026,
            basic_salary=Decimal('50000.00'),
            hra=Decimal('20000.00'),
            allowances_total=Decimal('4500.00'),
            gross_salary=Decimal('74500.00'),
            total_deductions=Decimal('6200.00'),
            net_salary=Decimal('68300.00')
        )
        pdf_buffer = generate_payslip_pdf(record)
        content = pdf_buffer.getvalue()
        # A valid PDF file begins with %PDF-
        self.assertTrue(content.startswith(b'%PDF-'))
        self.assertGreater(len(content), 1000)
