# Singapore Diabetes Care Knowledge Base
## Comprehensive Guide for Diabetes Management in Singapore

**Version:** 1.0  
**Last Updated:** February 2026  
**Purpose:** RAG Vector Database for Diabetes Patient Health Management Application  
**Target Audience:** Singaporean diabetes patients and healthcare providers

---

# SECTION 1: UNDERSTANDING DIABETES IN SINGAPORE

## 1.1 Diabetes Epidemiology in Singapore

### Prevalence Statistics
According to the MOH National Population Health Survey 2024 (tracking data from July 2023-June 2024), the prevalence of diabetes among Singapore residents aged 18-74 years was 9.1%, remaining stable compared to the 2019-2020 survey (9.5%). Over 400,000 Singaporeans are currently living with diabetes, with projections suggesting this number could reach 1 million by 2050 if no intervention is taken. The highest prevalence was in older adults aged 70-74 years at 22.0%. Approximately one-third of diabetics in Singapore are unaware they have the condition. Singapore ranks among the highest in the world for diabetic nephropathy, with 2 in 3 new cases of kidney failure attributed to diabetes. 

Notably, the prevalence of hypertension (33.8%) and hyperlipidemia (30.5%) also remain concerns, with about 1 in 3 Singapore residents affected by these conditions. The prevalence of obesity (BMI ≥30.0 kg/m²) increased significantly from 10.5% in 2019-2020 to 12.7% in 2023-2024.

**Source:** MOH National Population Health Survey 2024; Ministry of Health Singapore War on Diabetes Initiative

### Risk Factors for Singaporeans
Risk factors specific to the Singapore population include: age over 40 years, BMI above 23 kg/m² (Asian-specific threshold), waist circumference exceeding 90cm for men or 80cm for women, family history of diabetes in first-degree relatives, history of gestational diabetes, polycystic ovary syndrome (PCOS), hypertension, and dyslipidemia.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; Agency for Care Effectiveness (ACE)

---

## 1.2 Types of Diabetes

### Type 1 Diabetes Mellitus
Type 1 diabetes is an autoimmune condition where the pancreas produces little to no insulin. All patients with Type 1 diabetes must receive insulin therapy. Multiple daily injections (3 or more) or continuous subcutaneous insulin infusion (CSII or insulin pump therapy) may be required to achieve target glucose levels. In Singapore, GAD antibodies (GADAb) and Islet Cell Antibodies (ICA) are detectable in up to 40% and 20% of Type 1 diabetes cases respectively. Patients with Type 1 diabetes should have their thyroid function checked every 1-2 years.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

### Type 2 Diabetes Mellitus
Type 2 diabetes is characterized by insulin resistance and progressive beta-cell dysfunction. It accounts for approximately 90-95% of all diabetes cases. Risk factors include obesity, sedentary lifestyle, family history, and advancing age. In Singapore, lifestyle changes with modest weight loss and moderate physical activity can potentially reverse pre-diabetes and prevent progression to diabetes. Approximately 430,000 Singaporeans (14% aged 18-69 years) have pre-diabetes.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; ACE Appropriate Care Guide on Managing Pre-diabetes 2021

### Gestational Diabetes Mellitus (GDM)
Gestational diabetes is defined as the onset or first recognition of any degree of glucose intolerance during pregnancy. Women with a history of GDM require follow-up post-pregnancy as they have increased risk of developing Type 2 diabetes. The International Association of Diabetes and Pregnancy Study Groups (IADPSG) criteria are used for diagnosis.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

---

## 1.3 Diagnosis of Diabetes in Singapore

### Diagnostic Criteria
According to MOH Clinical Practice Guidelines, diabetes mellitus can be diagnosed if any of the following criteria are met:

1. **Fasting Plasma Glucose (FPG):** ≥7.0 mmol/L (126 mg/dL)
2. **2-Hour Post-Glucose Load (OGTT):** ≥11.1 mmol/L (200 mg/dL)
3. **Random Plasma Glucose:** ≥11.1 mmol/L (200 mg/dL) with symptoms of hyperglycemia
4. **HbA1c:** ≥6.5% (48 mmol/mol) - though HbA1c is not the primary recommended screening tool in Singapore's multi-ethnic population

Fasting plasma glucose measured in an accredited laboratory is the preferred test for diagnosis in Singapore.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

### Pre-diabetes Diagnosis
Pre-diabetes (Impaired Glucose Tolerance or Impaired Fasting Glucose) is diagnosed when:
- Fasting Plasma Glucose: 6.1-6.9 mmol/L (Impaired Fasting Glucose)
- 2-Hour OGTT: 7.8-11.0 mmol/L (Impaired Glucose Tolerance)
- HbA1c: 6.0-6.4% indicates intermediate risk

All subjects with fasting plasma glucose from 6.1 to 6.9 mmol/L should undergo a 75g oral glucose tolerance test to determine if they have impaired glucose tolerance or diabetes mellitus.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; ACE Managing Pre-diabetes Guide 2021

---

# SECTION 2: GLYCEMIC CONTROL AND TARGETS

## 2.1 HbA1c Targets

### General HbA1c Recommendations
According to Singapore MOH and ACE guidelines, target HbA1c should be individualized based on the patient's overall health status, in consultation with the patient.

**Standard Target:** For most non-pregnant adults with Type 1 or Type 2 diabetes, the HbA1c target should be ≤7.0% (53 mmol/mol). This provides a reasonable balance between reduction in risk of microvascular complications and risk of hypoglycemia.

**Stricter Target:** Lowering HbA1c target to ≤6.5% (47.5 mmol/mol) may be considered for some patients with Type 2 diabetes at doctor and patient judgement, if this can be achieved without significant hypoglycemia. Such patients include those with short duration of diabetes, long life expectancy, and no significant cardiovascular disease.

**Less Stringent Target:** HbA1c target of 7.0-8.5% (53-69.4 mmol/mol) may be adopted for patients vulnerable to harmful effects associated with tight glycemic control, including those with history of severe hypoglycemia, limited life expectancy, advanced microvascular or macrovascular complications, extensive comorbid conditions, or long-standing diabetes where achieving tighter control is difficult.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; ACE Clinical Guidance on Type 2 Diabetes Mellitus 2023

### Pediatric HbA1c Targets
Children and adolescents with Type 1 or Type 2 diabetes mellitus, and their families, should be informed that the target for long-term blood glucose control is an HbA1c level of less than 7.5% (58.5 mmol/mol) without frequent hypoglycemia.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

### HbA1c Monitoring Frequency
HbA1c should be measured:
- At least every 6 months for patients meeting treatment goals with stable glycemic control
- Every 3 months for patients not meeting glycemic goals or when therapy changes
- Results should be made available at the time the patient is seen

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

---

## 2.2 Self-Monitoring of Blood Glucose (SMBG)

### When SMBG is Recommended
Self-monitoring of blood glucose should be considered for:
- Patients at increased risk of developing hypoglycemia
- Patients on insulin therapy (3 or more times daily for Type 1 diabetes)
- Pregnant patients with pre-existing diabetes or gestational diabetes
- Patients on medications that may cause hypoglycemia

Consider the possibility of antecedent nocturnal hypoglycemia if fasting blood glucose is <4mmol/L.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

### Target Blood Glucose Ranges
- **Pre-meal (fasting):** 4.0-7.0 mmol/L
- **Post-meal (2 hours after eating):** <10.0 mmol/L
- **Bedtime:** 5.0-8.0 mmol/L

Blood glucose targets should be individually determined with a goal to achieving values as close to normal as possible.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; HealthHub Singapore

---

# SECTION 3: PHARMACOLOGICAL MANAGEMENT

## 3.1 Medications for Type 2 Diabetes

### First-Line Therapy: Metformin
Metformin is usually considered first-line pharmacotherapy after failing to meet glycemic targets despite lifestyle changes alone. Metformin decreases hepatic glucose release, enhances peripheral glucose disposal, and decreases intestinal glucose absorption. It is contraindicated in patients with significant renal impairment or conditions predisposing to lactic acidosis.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; ACE Clinical Guidance on T2DM 2023

### Second-Line and Add-On Therapies

**Sulfonylureas:** Can be considered as add-on therapy when glycemic control is the priority. If cost is a consideration and there are no concerns about hypoglycemia or weight gain, sulfonylureas can be considered. Examples available in Singapore include glipizide, gliclazide, and glimepiride.

**DPP-4 Inhibitors (Gliptins):** May be considered as add-on therapy. They work by prolonging the action of incretin hormones. Examples include sitagliptin, saxagliptin, linagliptin, and vildagliptin.

**SGLT-2 Inhibitors:** Consider adding for patients requiring cardiorenal risk reduction, irrespective of their need for improved glycemic control. They work by blocking glucose reabsorption in the kidneys. Benefits include cardiovascular protection, kidney protection, and weight loss (2-3 kg). Examples include empagliflozin, dapagliflozin, and canagliflozin.

**GLP-1 Receptor Agonists:** Consider adding for patients requiring cardiorenal risk reduction. They enhance glucose-dependent insulin secretion and suppress glucagon. Benefits include cardiovascular protection, weight loss (1.1-4.4 kg), and blood pressure reduction. Examples include liraglutide, semaglutide, and dulaglutide.

**Source:** ACE Clinical Guidance on Type 2 Diabetes Mellitus: Personalising Management with Non-Insulin Medications 2023; MOH Healthier SG Care Protocols

### When to Initiate Dual Therapy
Consider initiating dual therapy in patients in whom initial HbA1c is ≥1.5% above target, or those in whom monotherapy is not expected to be sufficient.

**Source:** ACE Clinical Guidance on T2DM 2023

### When to Consider Insulin
Insulin therapy should be considered if optimal combination oral therapy fails to attain target control (i.e., 2 consecutive HbA1c values failed to reach ≤8% over 3-6 months interval). In the setting of severely uncontrolled Type 2 diabetes (HbA1c >10%, random glucose consistently above 16.7 mmol/L), presence of ketonuria, or symptomatic diabetes with polyuria, polydipsia, and weight loss, insulin should be initiated.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; ACE Clinical Guidance on Initiating Basal Insulin 2022

---

## 3.2 SGLT-2 Inhibitors: Detailed Guidance

### Cardiorenal Benefits
SGLT-2 inhibitors have demonstrated significant benefits in reducing:
- Major adverse cardiovascular events (11% reduction)
- Hospitalization for heart failure (31% reduction)
- Progression of kidney disease (including reduction in macroalbuminuria and slowing eGFR decline)

These benefits are observed irrespective of the need for improved glycemic control.

**Source:** ACE Clinical Guidance on T2DM 2023; Circulation 2019 Meta-analysis

### Precautions and Monitoring
- Reports of euglycemic diabetic ketoacidosis (DKA) - educate patients on symptoms
- Necrotizing fasciitis of the perineum (Fournier's gangrene) - rare but serious
- Dose adjustments may be required based on eGFR
- Risk of hypoglycemia increases when used with sulfonylureas or insulin
- May cause genital mycotic infections and urinary tract infections
- Volume depletion in elderly or those on diuretics

**Source:** ACE Clinical Guidance on T2DM 2023

---

## 3.3 GLP-1 Receptor Agonists: Detailed Guidance

### Cardiovascular Benefits
GLP-1 receptor agonists have demonstrated:
- 12% reduction in major adverse cardiovascular events (MACE)
- Significant benefit in patients with established atherosclerotic cardiovascular disease
- Stroke prevention effects
- Potential reduction in kidney disease progression

**Source:** ACE Clinical Guidance on T2DM 2023; American Heart Association journals

### Precautions and Monitoring
- May delay gastric emptying; not recommended in patients with clinically meaningful gastroparesis
- Reports of diabetic retinopathy complications with semaglutide (may be related to rapid improvement in blood glucose control)
- Gastrointestinal side effects (nausea, vomiting, diarrhea) common initially
- If HbA1c is well-controlled at baseline or known history of frequent hypoglycemic events, wean or stop sulfonylurea when starting GLP-1 RA
- Start at low dose and titrate gradually to minimize GI side effects

**Source:** ACE Clinical Guidance on T2DM 2023

---

# SECTION 4: HYPERTENSION MANAGEMENT IN DIABETES

## 4.1 Blood Pressure Classification and Diagnosis

### Singapore MOH Classification (2017)
| Category | Systolic BP (mmHg) | Diastolic BP (mmHg) |
|----------|-------------------|---------------------|
| Normal | <120 | and <80 |
| High-Normal | 120-129 | and/or 80-84 |
| Grade 1 Hypertension | 130-139 | and/or 85-89 |
| Grade 2 Hypertension | 140-159 | and/or 90-99 |
| Grade 3 Hypertension | ≥160 | and/or ≥100 |

**Source:** MOH Clinical Practice Guidelines on Hypertension 2017

### Blood Pressure Measurement
- Allow patient to sit or lie down for at least 3 minutes before measuring
- Take an average of 2 seated BP measurements separated by 2 minutes
- If first two readings differ by 5 mmHg or more, further readings should be obtained and averaged
- Repeat BP measurements on at least 2 separate occasions
- Consider ambulatory or home BP monitoring where appropriate (note: ambulatory/home BP readings tend to be lower than clinic readings)

**Source:** MOH Primary Care Pages - Hypertension Care Protocol; ACE Clinical Guidance on Hypertension 2023

## 4.2 Blood Pressure Targets for Diabetic Patients

### General Target
For most diabetic patients, the target blood pressure is <140/80 mmHg.

### Individualized Targets
- **Patients aged 80 years or more:** Target <150/90 mmHg
- **Patients with CKD and moderate-severe albuminuria:** Target <140/80 mmHg (lower may be beneficial)
- **Lower limit:** Do not lower BP below 120/70 mmHg as evidence of benefit beyond this threshold is inconsistent, and potential for increased side effects can lead to treatment discontinuation

**Source:** MOH Clinical Practice Guidelines on Hypertension 2017; ACE Clinical Guidance on Hypertension 2023

## 4.3 Antihypertensive Therapy in Diabetes

### First-Line Agents
For diabetic patients with hypertension, recommended first-line agents include:
- ACE inhibitors (ACEi)
- Angiotensin Receptor Blockers (ARBs)
- Calcium Channel Blockers (CCBs)
- Thiazide diuretics

### Preferred Agents for Diabetic Nephropathy
In diabetic patients with micro- or macroalbuminuria, ACE inhibitors or ARBs should be used to reduce the risk or slow progression of nephropathy.

### Combination Therapy
Starting with dual therapy may be appropriate if:
- Greater reduction in BP is required to reach targets (SBP/DBP ≥20/10 mmHg above target)
- Grade 2 hypertension or higher (clinic BP ≥160/100 mmHg)
- Comorbidities such as diabetes or CKD requiring more intensive treatment

**Source:** MOH Clinical Practice Guidelines on Hypertension 2017; MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

---

# SECTION 5: LIPID MANAGEMENT IN DIABETES

## 5.1 Lipid Targets and Screening

### Reference Ranges (Singapore)
| Parameter | Desirable | Borderline High | High |
|-----------|-----------|-----------------|------|
| Total Cholesterol | <5.2 mmol/L | 5.2-6.1 mmol/L | ≥6.2 mmol/L |
| LDL Cholesterol | <3.4 mmol/L | 3.4-4.0 mmol/L | 4.1-4.8 mmol/L |
| HDL Cholesterol | ≥1.0 mmol/L (men), ≥1.3 mmol/L (women) | - | <1.0 mmol/L (abnormal) |
| Triglycerides | <2.3 mmol/L | 2.3-4.4 mmol/L | ≥4.5 mmol/L |

**Source:** Health Promotion Board Singapore; MOH Clinical Practice Guidelines on Lipids 2016

### LDL-C Targets Based on Risk
- **Very High Risk (established ASCVD):** LDL-C <1.8 mmol/L (70 mg/dL) or ≥50% reduction
- **High Risk (diabetes with complications):** LDL-C <2.1 mmol/L (80 mg/dL)
- **Diabetes without ASCVD:** LDL-C <2.6 mmol/L (100 mg/dL) for most patients

For patients with diabetes and overt cardiovascular disease and/or chronic kidney disease, LDL-C should be lowered to target of <2.1 mmol/L.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; MOH Clinical Practice Guidelines on Lipids 2016; ACE Clinical Guidance on Lipid Management 2023

## 5.2 Pharmacological Management

### Statin Therapy
- For most patients with Type 2 diabetes where LDL-C is >2.6 mmol/L, an HMG-CoA reductase inhibitor (statin) should be started concurrently with therapeutic lifestyle modification
- Higher statin sensitivity may be present in Asian patients; start at lower doses and titrate
- Select a statin for patients with diabetes mellitus, chronic kidney disease, or high 10-year CV risk (>20%)

### Intensive Lipid-Lowering Therapy
Intensive lipid lowering (maximally-tolerated statin plus ezetimibe) is recommended for:
- Established atherosclerotic cardiovascular disease (ASCVD)
- Familial hypercholesterolemia (FH)
- High-risk diabetes with complications and/or long duration

Consider adding PCSK9 inhibitors (alirocumab, evolocumab) or inclisiran for further risk reduction if LDL-C target not achieved with maximally-tolerated statin and ezetimibe.

**Source:** ACE Clinical Guidance on Lipid Management 2023; Academy of Medicine Singapore CPG on Lipids 2023

### Triglyceride Management
- Elevated triglycerides (>1.7 mmol/L) contribute to overall cardiovascular risk
- For severe hypertriglyceridemia (TG >10 mmol/L), omega-3 fish oils 3-12g/day should be added to fibrates
- Fibrates may be added for patients with TG >4.5 mmol/L despite statin therapy to reduce acute pancreatitis risk
- Fenofibrate is preferred over gemfibrozil as add-on to statins due to lower myopathy risk

**Source:** MOH Clinical Practice Guidelines on Lipids 2016; ACE Clinical Guidance 2023

---

# SECTION 6: DIABETIC KIDNEY DISEASE (NEPHROPATHY)

## 6.1 Screening and Diagnosis

### Annual Screening Requirements
- Perform annual test to assess urine albumin excretion in Type 1 diabetic patients with diabetes duration of 5 years, and in all Type 2 diabetic patients starting at diagnosis
- Measure serum creatinine at least annually in all adults with diabetes to estimate GFR and stage CKD if present
- Use the Modification of Diet in Renal Disease (MDRD) equation to estimate renal function when eGFR is below 60 mL/min/1.73m²

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

### CKD Staging
| Stage | eGFR (mL/min/1.73m²) | Description |
|-------|---------------------|-------------|
| G1 | ≥90 | Normal or high |
| G2 | 60-89 | Mildly decreased |
| G3a | 45-59 | Mildly to moderately decreased |
| G3b | 30-44 | Moderately to severely decreased |
| G4 | 15-29 | Severely decreased |
| G5 | <15 | Kidney failure |

### Albuminuria Categories
| Category | ACR (mg/mmol) | ACR (mg/g) |
|----------|---------------|------------|
| A1 (Normal to mildly increased) | <3 | <30 |
| A2 (Moderately increased/Microalbuminuria) | 3-30 | 30-300 |
| A3 (Severely increased/Macroalbuminuria) | >30 | >300 |

**Source:** KDIGO 2020/2022 Guidelines; MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

## 6.2 Management of Diabetic Nephropathy

### Key Management Strategies
To reduce the risk or slow progression of nephropathy:
1. **Optimized glucose control** (Grade A recommendation)
2. **Optimized blood pressure control** (Grade A recommendation)
3. **Optimized lipid control** (Grade A recommendation)
4. **ACE inhibitors or ARBs** for patients with micro- or macroalbuminuria (Grade A recommendation)
5. **Protein restriction:** 0.8-1.0 g/kg body weight/day in earlier CKD stages; 0.8 g/kg/day in later stages

### SGLT-2 Inhibitors for Kidney Protection
SGLT-2 inhibitors reduce the risk of kidney failure by 31% and slow progression of CKD. They should be considered for patients with diabetes and CKD, irrespective of glycemic control needs.

### GLP-1 Receptor Agonists for Kidney Protection
GLP-1 RAs also reduce the risk of progression of kidney disease, including macroalbuminuria.

### Monitoring Requirements
When ACE inhibitors, ARBs, or diuretics are used, monitor serum creatinine and potassium levels for development of acute kidney disease and hyperkalemia.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; KDIGO 2022 Clinical Practice Guideline; ACE Clinical Guidance on T2DM 2023

### Singapore Statistics
Diabetes is the number one cause of kidney failure in Singapore, accounting for 67% of new cases. Singapore ranks top in the world for diabetic nephropathy.

**Source:** National Kidney Foundation Singapore

---

# SECTION 7: DIABETIC EYE DISEASE (RETINOPATHY)

## 7.1 Screening Guidelines

### Screening Schedule
- **Type 1 Diabetes:** First eye examination within 3-5 years after diagnosis, then annually
- **Type 2 Diabetes:** First eye examination at diagnosis, then annually
- **Gestational Diabetes:** Eye examination in first trimester and monitoring throughout pregnancy

The Singapore Ministry of Health guidelines recommend that people with diabetes be screened annually for diabetic eye disease.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; Singapore National Eye Centre

### Singapore Integrated Diabetic Retinopathy Programme (SiDRP)
SiDRP is Singapore's national telemedicine diabetic retinopathy screening program. Features include:
- Real-time assessment of DR from photographs by centralized trained readers
- Two-field retinal images taken using retinal camera at polyclinics
- Reports generated within 1 business day (often within the hour)
- Available at all 21 polyclinics across SingHealth, NHG, and NUP
- Uses AI-powered SELENA+ deep learning system to assist with grading

**Source:** Singapore National Eye Centre; Singapore Eye Research Institute

## 7.2 Classification of Diabetic Retinopathy

### Stages of Retinopathy
1. **Non-Proliferative Diabetic Retinopathy (NPDR)**
   - Mild: Microaneurysms only
   - Moderate: More than microaneurysms but less than severe
   - Severe: Extensive intraretinal hemorrhages, venous beading, or intraretinal microvascular abnormalities

2. **Proliferative Diabetic Retinopathy (PDR)**
   - New vessel formation on the disc or elsewhere
   - Vitreous or preretinal hemorrhage
   - High risk of severe vision loss

### Diabetic Macular Edema (DME)
Swelling of the macula due to fluid leakage; primary cause of vision loss in diabetic patients.

**Source:** Singapore National Eye Centre; International Council of Ophthalmology Guidelines 2017

## 7.3 Risk Factors and Prevention

### Risk Factors for DR Progression
- Duration of diabetes (most important factor)
- Poor blood sugar control
- High blood pressure
- High cholesterol
- Pregnancy (can accelerate DR progression)
- Kidney complications (concomitant presence increases risk)

### Prevention Strategies
- Good control of blood glucose (hyperglycemia is the key initiator)
- Blood pressure control
- Lipid control
- Addition of fenofibrate may play a role in prevention
- Regular screening for early detection

**Source:** Singapore National Eye Centre; MOH Clinical Practice Guidelines

## 7.4 Treatment Options

### Laser Photocoagulation
Pan-retinal photocoagulation (PRP) remains standard of care for proliferative diabetic retinopathy.

### Anti-VEGF Injections
Intravitreal injections of anti-VEGF drugs (ranibizumab, aflibercept, bevacizumab) are gold standard for center-involving diabetic macular edema. However, significant cost and treatment burden (median 10 injections over 2 years) are barriers to optimal care.

### Referral Criteria
Refer to ophthalmologist if:
- Any degree of diabetic retinopathy is detected
- Cannot assess retina adequately
- Patient has visual symptoms

**Source:** Singapore National Eye Centre; MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

---

# SECTION 8: DIABETIC FOOT CARE

## 8.1 Foot Screening and Risk Assessment

### Annual Foot Examination
All individuals with diabetes should receive an annual comprehensive foot examination to identify high-risk foot conditions.

### Risk Stratification (ACE Guidelines)
| Risk Category | Features | Review Frequency |
|---------------|----------|------------------|
| Low Risk | Normal sensation, no deformity, good pulses | Annually |
| Moderate Risk | Loss of protective sensation OR peripheral arterial disease OR foot deformity | Every 6 months |
| High Risk | Previous ulcer/amputation OR combined risk factors | Every 3-4 months |

**Source:** Agency for Care Effectiveness (ACE) Foot Assessment Guidelines 2024; MOH Healthier SG Care Protocols

### Components of Foot Assessment
1. **Inspection:** Check for blisters, cuts, skin maceration, redness, swelling, bruising, wounds (especially between toes)
2. **Neurological Assessment:** Monofilament test (10g), vibration perception testing
3. **Vascular Assessment:** Pedal pulses palpation, ankle-brachial index if indicated
4. **Footwear Assessment:** Proper fitting, open-toe vs closed shoes

**Source:** ACE Foot Assessment Guidelines 2024

## 8.2 Prevention of Diabetic Foot Ulcers

### Patient Education (Key Messages)
1. **Daily Inspection:** Check feet every day for blisters, cuts, sores, corns, or swelling
2. **Never Go Barefoot:** Always wear comfortable, properly fitting shoes
3. **Daily Washing:** Use mild soap and lukewarm water, dry thoroughly (especially between toes)
4. **Moisturize:** Apply moisturizer to prevent dryness and cracks, but avoid between toes
5. **Nail Care:** Cut nails straight across, file corners, avoid cutting too short
6. **No Sharp Tools:** Use pumice stone or nail file for calluses; never use sharp tools
7. **Avoid Heat Injury:** Don't use hot water bottles or heating pads on feet

**Source:** Singapore General Hospital; MOH Clinical Practice Guidelines; ACE Guidelines

### Singapore Statistics on Foot Complications
- 84% of non-traumatic limb amputations in diabetics are preceded by foot ulcers
- Diabetics are 15-25 times more at risk of limb amputation compared to non-diabetics
- Approximately 25% of diabetics will develop a foot wound or ulcer in their lifetime
- A multidisciplinary approach can reduce amputation rates by up to 50%

**Source:** National University Hospital Singapore; Singapore General Hospital

## 8.3 Management of Diabetic Foot Problems

### V.I.P. of Wound Healing
When active diabetic foot ulcers are detected:
- **V - Vascular:** Ensure adequate blood supply to the foot
- **I - Infection:** Control and treat infection
- **P - Pressure:** Offload pressure from the wound

### Referral Criteria (Urgent)
Refer to emergency department immediately if:
- Signs of moderate/severe infection (wet gangrene, abscess, osteomyelitis)
- Presence of peripheral arterial disease/ischemia with infection (regardless of severity)

### Multidisciplinary Care
Singapore General Hospital operates the RAFT (Rapid Access FooT) clinic - a multidisciplinary clinic involving vascular specialists, endocrinologists, and podiatrists for timely diabetes foot treatment.

**Source:** Singapore General Hospital; SingHealth Duke-NUS Diabetes Centre

---

# SECTION 9: CARDIOVASCULAR DISEASE IN DIABETES

## 9.1 Cardiovascular Risk Assessment

### Diabetes as CV Risk Factor
Patients with Type 2 diabetes have a 2-4 fold increased risk of developing cardiovascular disease, including coronary artery disease, stroke, peripheral arterial disease, cardiomyopathy, atrial fibrillation, and heart failure.

### Singapore-Modified Framingham Risk Score (SG-FRS-2023)
The SG-FRS-2023 is recalibrated for the Singapore population and generates:
- 10-year cardiovascular risk estimate
- Target LDL cholesterol levels
- Target blood pressure levels

**Source:** ACE Clinical Guidance on Lipid Management 2023; Saw Swee Hock School of Public Health

### Risk Categories
- **Very High Risk:** Established ASCVD, diabetes with target organ damage, or 10-year risk >20%
- **High Risk:** Diabetes without ASCVD but with multiple risk factors
- **Moderate Risk:** 10-year risk 10-20%
- **Low Risk:** 10-year risk <10%

**Source:** ACE Clinical Guidance on Lipid Management 2023

## 9.2 Primary Prevention

### Risk Factor Modification
1. **Glycemic Control:** Maintain HbA1c at target
2. **Blood Pressure Control:** Target <140/80 mmHg for most diabetics
3. **Lipid Management:** Statin therapy for LDL-C reduction
4. **Smoking Cessation:** Use of tobacco in any form should stop
5. **Weight Management:** 10 kg weight loss reduces LDL-C by 0.2 mmol/L
6. **Physical Activity:** 150-300 minutes/week moderate intensity

### Aspirin for Primary Prevention
Consider low-dose aspirin for primary prevention in diabetic individuals:
- Age 50 years for men, 60 years for women
- With at least one additional cardiovascular risk factor
- Without high bleeding risk

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014

## 9.3 Cardiorenal Protection with SGLT-2 Inhibitors and GLP-1 RAs

### When to Prioritize Cardiorenal Protection
For patients with Type 2 diabetes AND any of the following:
- Established atherosclerotic cardiovascular disease (ASCVD)
- Heart failure
- Diabetic kidney disease
- High risk for ASCVD (end-organ damage, multiple CV risk factors)

Consider SGLT-2 inhibitors and/or GLP-1 receptor agonists for cardiorenal risk reduction, irrespective of glycemic control needs.

### Evidence for Benefit
- **SGLT-2 Inhibitors:** Reduce hospitalization for heart failure by 31%, reduce kidney disease progression
- **GLP-1 RAs:** Reduce MACE by 12%, reduce stroke risk

Combined use of both classes may provide complementary benefits.

**Source:** ACE Clinical Guidance on T2DM 2023; American Diabetes Association Standards of Care 2025; KDIGO Guidelines

---

# SECTION 10: NUTRITION AND DIET

## 10.1 General Dietary Principles

### My Healthy Plate (Singapore HPB)
The Health Promotion Board recommends the "My Healthy Plate" approach:
- **Half the plate:** Non-starchy vegetables (spinach, carrots, lettuce, broccoli)
- **Quarter of the plate:** Whole grains and starchy carbohydrates (brown rice, whole grain bread)
- **Quarter of the plate:** Lean protein (fish, chicken, tofu, eggs)

**Source:** Health Promotion Board Singapore; National University Hospital

### Key Dietary Recommendations
1. **Balanced Diet:** Include variety of foods from all food groups
2. **Consistent Carbohydrates:** Eat appropriate and consistent amount of carbohydrate at each meal
3. **Regular Meals:** Have meals at similar timing each day
4. **Increase Fiber:** Include wholegrain products (brown rice, whole-meal bread, oats)
5. **Reduce Fat:** Limit saturated and trans fats
6. **Reduce Salt:** High salt intake associated with hypertension
7. **Limit Sugar:** Minimize added sugars and sugary drinks

**Source:** HealthHub Singapore - Healthy Eating for Managing Diabetes

## 10.2 Carbohydrate Management

### Understanding Carbohydrates
Carbohydrates are converted into glucose during digestion and directly impact blood sugar levels. They should provide approximately half of energy needs but portion control is essential.

### Carbohydrate Counting
- General aim: 45-60 grams of carbohydrate per main meal
- Individual needs vary based on lifestyle, medication, and blood sugar control
- 1 serving = approximately 15g carbohydrates

### Examples of 15g Carbohydrate Portions
- 4 level tablespoons cooked brown rice (~55g)
- 1 slice wholemeal bread
- 3 heaped tablespoons dry instant oats (~22g)
- 1 medium fruit
- ½ piece plain prata

**Source:** Tan Tock Seng Hospital Nutrition Department; Health Promotion Board Singapore

### Glycemic Index (GI)
- Choose lower GI foods (whole grains, legumes, non-starchy vegetables)
- Lower GI foods cause slower rise in blood glucose
- Brown rice provides more fiber than white rice (same carbohydrate content)

**Source:** HealthHub Singapore; Singapore General Hospital

## 10.3 Diabetes-Friendly Local Foods

### Healthier Hawker Choices
- **Yong Tau Foo:** High in vegetables, choose tofu and fish over processed items
- **Thunder Tea Rice (Lei Cha):** High in vegetables and fiber; request brown rice
- **Chapati:** More fiber than roti prata; pair with vegetables and lean protein
- **Chicken Rice:** Ask for less rice, choose steamed over roasted
- **Fish Soup with noodles:** Choose soup-based over fried; ask for less noodles
- **Economical Rice:** Load up on vegetables, choose steamed fish, limit rice portion

### Foods to Limit
- Fried foods (roti prata, char kway teow)
- Sweetened beverages
- Desserts with high sugar content
- Processed meats
- Dishes with heavy gravies

**Source:** Health Promotion Board Singapore; RunSociety Singapore

## 10.4 Special Considerations

### Alcohol
- Alcohol can cause hypoglycemia, especially in those on insulin or sulfonylureas
- If drinking, consume with food
- Limit intake and account for carbohydrates in mixed drinks

### "Diabetic" Food Products
Not essential and may be misleading:
- Often contain artificial sweeteners (sorbitol) which may have laxative effect
- May still be high in fat
- Still contain carbohydrates from flour, milk, fruit

**Source:** HealthHub Singapore; MOH Clinical Practice Guidelines

---

# SECTION 11: PHYSICAL ACTIVITY

## 11.1 Singapore Physical Activity Guidelines

### Recommendations for Adults (18-64 years)
- **Aerobic Activity:** 150-300 minutes of moderate-intensity OR 75-150 minutes of vigorous-intensity per week
- **Muscle Strengthening:** At least 2 days per week targeting major muscle groups
- **Flexibility/Balance:** Include stretching and balance activities
- **Reduce Sedentary Time:** Break up prolonged sitting

**Source:** Health Promotion Board Singapore Physical Activity Guidelines 2022

### Intensity Definitions
- **Moderate Intensity:** Can talk but cannot sing (brisk walking, cycling, swimming)
- **Vigorous Intensity:** Neither singing nor prolonged talking is possible (jogging, fast cycling, aerobic classes)

Every minute of vigorous-intensity activity counts as 2 minutes of moderate-intensity.

**Source:** Health Promotion Board Singapore; Sport Singapore

## 11.2 Exercise Benefits for Diabetes

### Metabolic Benefits
- Improves body's ability to use glucose
- Decreases insulin resistance
- Aerobic training effect similar to some oral diabetic medications
- Weight training preserves muscle tissue
- 150 minutes/week of moderate exercise can achieve 0.66% reduction in HbA1c

### Combined Benefits
Physical activity paired with nutrition intervention for weight loss can help achieve:
- Improved blood sugar control
- Weight loss (5-7% body weight target)
- Better lipid profile
- Lower blood pressure

**Source:** Singapore General Hospital; HealthXchange Singapore

## 11.3 Exercise Precautions for Diabetics

### Before Exercise
- Measure glucose level before exercising
- If on insulin, avoid exercising during peak insulin action
- Consider reducing insulin dose by 2-4 units if exercise cannot be avoided during peak action

### During Exercise
- Carry fast-acting carbohydrates
- Stop if hypoglycemia symptoms occur
- For moderate pain from peripheral arterial disease (claudication), rest until pain completely resolves

### Hypoglycemia Warning Signs During Exercise
- Shakiness
- Dizziness
- Sweating
- Hunger
- Confusion

If blood sugar <4 mmol/L, stop exercise and treat with 15g fast-acting carbohydrates.

**Source:** HealthHub Diabetes Hub; Singapore General Hospital

## 11.4 Practical Tips

### F.I.T.T. Principle
- **Frequency:** 5-7 days per week
- **Intensity:** Moderate (talk test)
- **Time:** 150-300 minutes per week total
- **Type:** Combination of aerobic, resistance, and flexibility

### Footwear for Diabetics
- Invest in proper footwear
- Wear socks made of polyester or cotton-polyester blend to prevent blisters
- Check feet after exercise for any injuries

### Starting an Exercise Program
- Get medical clearance if new to exercise
- Start slowly and progress gradually
- Consider supervision for weight training
- Learn correct posture and position to prevent injuries

**Source:** Singapore General Hospital; Health Promotion Board

---

# SECTION 12: HYPOGLYCEMIA MANAGEMENT

## 12.1 Definition and Causes

### Definition
Hypoglycemia (low blood glucose) is defined as blood glucose <4.0 mmol/L (<70 mg/dL) in Singapore.

### Classification
- **Mild-Moderate:** Blood glucose 55-70 mg/dL (3.0-4.0 mmol/L) - can self-treat
- **Severe:** Blood glucose <55 mg/dL (<3.0 mmol/L) - may need assistance

### Common Causes
- Taking too much insulin or certain oral diabetes medications (sulfonylureas)
- Delayed or missed meals
- Eating less than usual
- Excessive physical activity
- Alcohol consumption without food
- Altered timing of medications

**Source:** Singapore General Hospital; American Diabetes Association

## 12.2 Recognition of Symptoms

### Early Warning Signs
- Shakiness
- Sweating
- Hunger
- Palpitations
- Anxiety
- Pale skin

### More Severe Symptoms
- Confusion
- Difficulty concentrating
- Slurred speech
- Blurred vision
- Headache
- Seizures
- Loss of consciousness

### Hypoglycemia Unawareness
Some patients may not recognize symptoms (hypoglycemia unawareness). This is more common in:
- Long-standing diabetes
- Frequent hypoglycemic episodes
- Use of beta-blockers

**Source:** Singapore General Hospital; HealthXchange Singapore

## 12.3 The 15-15 Rule

### Treatment Protocol
1. **Check Blood Glucose:** If <4.0 mmol/L, treat immediately
2. **Consume 15g Fast-Acting Carbohydrates**
3. **Wait 15 Minutes**
4. **Recheck Blood Glucose**
5. **Repeat if Still <4.0 mmol/L**

### Examples of 15g Fast-Acting Carbohydrates
- 3-4 glucose tablets
- 1 tube glucose gel
- ½ cup (120ml) fruit juice
- ½ cup (120ml) regular soft drink (not diet)
- 1 tablespoon honey or sugar
- 5-6 jellybeans or hard candies

### Foods to AVOID for Treating Hypoglycemia
- Chocolate (fat slows sugar absorption)
- Foods high in fiber
- Baked goods (high in fat)
- Protein-rich foods alone

**Source:** Singapore General Hospital; American Diabetes Association; CDC

## 12.4 Severe Hypoglycemia

### When to Seek Emergency Care (Call 995)
- Blood glucose remains <4.0 mmol/L after repeated treatments
- Patient loses consciousness
- Patient unable to swallow safely
- Seizures occur

### Glucagon Emergency
- Injectable glucagon is the best way to treat severe hypoglycemia
- Available by prescription
- Family members/friends should know location and how to use it
- Patient usually wakes within 15 minutes after injection
- After glucagon injection, contact doctor immediately

### Post-Hypoglycemia
- Blood glucose may fall again ~1 hour after treatment
- If next meal >1 hour away, eat additional snack with 15g longer-acting carbohydrates (crackers with cheese, half a sandwich)

**Source:** Singapore General Hospital; CDC; American Diabetes Association

## 12.5 Prevention Strategies

### Key Prevention Tips
- Eat regular, balanced meals at consistent times
- Don't skip meals
- Monitor blood glucose regularly
- Adjust food intake and medication according to exercise routine
- Carry fast-acting carbohydrates at all times
- Wear diabetes identification

### Education for Family and Friends
- Teach recognition of hypoglycemia symptoms
- Show where glucose tablets/glucagon are kept
- Train on how to administer glucagon
- Know when to call for emergency help

**Source:** Singapore General Hospital; HealthXchange Singapore

---

# SECTION 13: SPECIAL POPULATIONS AND CIRCUMSTANCES

## 13.1 Elderly Patients

### Considerations
- Less stringent HbA1c targets may be appropriate (7.0-8.5%)
- Higher risk of hypoglycemia and its consequences
- Multiple comorbidities common
- Polypharmacy concerns
- Cognitive impairment may affect self-management

### Lipid Management in Elderly
- For patients >75 years on statin with LDL-C <2.1 mmol/L, no need to reduce therapy if well-tolerated
- Starting dose of statins in CKD should be low (e.g., 10 mg simvastatin or equivalent)

**Source:** MOH Clinical Practice Guidelines; ACE Guidelines

## 13.2 Pregnancy and Diabetes

### Pre-pregnancy Counseling
Women with diabetes who are in the reproductive age group should receive pre-pregnancy counseling.

### During Pregnancy
- Eye examination in first trimester and monitoring throughout
- Pregnancy can influence progression of diabetic retinopathy
- More frequent eye examinations required
- Statins are contraindicated in pregnancy and breastfeeding

### Gestational Diabetes Follow-up
Women with history of gestational diabetes require follow-up post-pregnancy due to increased risk of Type 2 diabetes.

**Source:** MOH Clinical Practice Guidelines on Diabetes Mellitus 2014; ACE Guidelines

## 13.3 Fasting (Ramadan)

### Risk Assessment Before Ramadan
Patients should consult healthcare providers before fasting. Considerations include:
- Type of diabetes medication
- Risk of hypoglycemia
- Overall health status
- Previous fasting experience

### Management During Fasting
- Blood glucose monitoring is important
- Medication timing and doses may need adjustment
- Break fast immediately if hypoglycemia occurs
- Stay hydrated during non-fasting hours

**Source:** MOH Healthier SG Care Protocols - Diabetes Mellitus

## 13.4 Travel Considerations

### Planning Ahead
- Carry sufficient medications and supplies
- Keep medications in carry-on luggage
- Carry letter from doctor listing medications
- Consider time zone changes for insulin timing
- Check blood glucose more frequently

### Managing Time Zone Changes
- For travel across time zones, insulin adjustment may be needed
- Consult diabetes care team before travel

**Source:** MOH Clinical Practice Guidelines; Diabetes Singapore

## 13.5 Sick Day Management

### Key Principles
- Never stop taking diabetes medication (especially insulin) even if not eating normally
- Monitor blood glucose more frequently
- Stay hydrated
- Test for ketones if blood glucose consistently >15 mmol/L

### When to Seek Medical Help
- Persistent vomiting or diarrhea
- Blood glucose remains high despite increased medication
- Presence of ketones
- Difficulty breathing
- Unable to eat or drink

**Source:** MOH Clinical Practice Guidelines; American Diabetes Association

---

# SECTION 14: HEALTHCARE RESOURCES IN SINGAPORE

## 14.1 Healthier SG Program

### Overview
The Healthier SG program, launched in 2023, encourages Singaporeans to enroll with a family doctor for coordinated chronic disease management. It emphasizes preventive care and a shift from reactive treatments to proactive healthcare.

### Eligibility
- Primary focus on Singapore citizens aged 40 years and above
- Invitations sent progressively to residents

### Benefits for Diabetes Patients
- Regular reviews with enrolled GP
- Access to subsidized chronic medications
- Coordinated referrals to specialists
- Diabetes Patient Dashboard on NEHR for monitoring
- MediSave usage without 15% cash co-payment at enrolled clinics

### Healthier SG Chronic Tier
Effective from February 2024, CHAS/PG/MG cardholders with chronic conditions can opt for the Healthier SG Chronic Tier:
- Access to selected common chronic medications at prices comparable to polyclinics
- Percentage-based subsidies for whitelisted drug products
- Additional subsidies for Medication Assistance Fund (MAF) medications for CHAS Blue and Orange cardholders
- Particularly benefits those with higher medication needs whose bills exceed CHAS annual subsidy limits

**Source:** MOH Healthier SG; Primary Care Pages Singapore; Healthier SG Chronic Tier Guidelines

## 14.2 Chronic Disease Management Programme (CDMP)

### Overview
The Chronic Disease Management Programme (CDMP) was first introduced in 2006 to reduce out-of-pocket expenses for outpatient management of chronic conditions and promote health-seeking behavior. Eligible patients can utilize their MediSave at MediSave-accredited healthcare entities.

### Coverage
CDMP covers 23 chronic diseases including diabetes mellitus/pre-diabetes, hypertension, hyperlipidemia, chronic kidney disease, ischemic heart disease, stroke, and osteoarthritis among others.

### MediSave Usage
- Patients with complex chronic conditions can use up to $700 per patient yearly
- Other patients can use up to $500 per patient yearly for treatments
- Since 1 February 2024, the 15% co-payment is waived for patients seeking CDMP treatment at their enrolled Healthier SG clinics
- Each claim was previously subject to a 15% co-payment in cash

### Where to Access CDMP
- All polyclinics
- All public hospital Specialist Outpatient Clinics (SOCs)
- Over 1,250 GP clinics and private specialist clinics accredited for MediSave

**Source:** MOH CDMP Guidelines 2024; MOH Healthier SG

## 14.3 Screen for Life (SFL) Programme

### Diabetes Screening
- Enhanced subsidies available for health screening
- Diabetes Risk Assessment (DRA) tool for adults 18-39 years
- Regular screening recommended every 3 years for those 40 and above

**Source:** Health Promotion Board

## 14.4 Key Healthcare Contacts

### SingHealth Duke-NUS Diabetes Centre Hotlines
- Singapore General Hospital: 6326 6060
- Changi General Hospital: 6788 3003
- Sengkang General Hospital: 6930 6000
- KK Women's and Children's Hospital: 6692 2984
- Singapore National Eye Centre: 6322 9399

### Emergency
- Ambulance: 995

**Source:** SingHealth

---

# SECTION 15: VACCINATIONS FOR DIABETIC PATIENTS

## 15.1 Recommended Vaccinations

### Influenza (Flu) Vaccine
- Recommended annually for all diabetic patients
- Reduces risk of serious flu complications

### Pneumococcal Vaccine
- Recommended for diabetic patients
- Protects against pneumococcal disease

### COVID-19 Vaccine
- Recommended for all eligible diabetic patients
- Follow MOH guidelines for boosters

### Hepatitis B Vaccine
- Consider for unvaccinated diabetic adults

**Source:** MOH Adult Vaccination Care Protocol; MOH Clinical Practice Guidelines

---

# APPENDIX A: QUICK REFERENCE TARGETS

## Glycemic Control
| Parameter | Target |
|-----------|--------|
| HbA1c (most adults) | ≤7.0% |
| HbA1c (stringent) | ≤6.5% |
| HbA1c (less stringent) | 7.0-8.5% |
| Fasting glucose | 4.0-7.0 mmol/L |
| Post-meal glucose (2h) | <10.0 mmol/L |

## Blood Pressure
| Population | Target |
|------------|--------|
| Diabetic patients | <140/80 mmHg |
| Elderly ≥80 years | <150/90 mmHg |
| Lower limit | Not below 120/70 mmHg |

## Lipids
| Parameter | Target |
|-----------|--------|
| LDL-C (very high risk) | <1.8 mmol/L |
| LDL-C (high risk) | <2.1 mmol/L |
| LDL-C (diabetes) | <2.6 mmol/L |
| Triglycerides | <2.3 mmol/L |
| HDL-C (men) | ≥1.0 mmol/L |
| HDL-C (women) | ≥1.3 mmol/L |

## Body Composition (Asian Criteria)
| Parameter | Cut-off |
|-----------|---------|
| BMI (overweight) | ≥23 kg/m² |
| BMI (obese) | ≥27.5 kg/m² |
| Waist (men) | <90 cm |
| Waist (women) | <80 cm |

---

# APPENDIX B: COMMON MEDICATIONS IN SINGAPORE

## Oral Diabetes Medications
| Class | Examples | Key Points |
|-------|----------|------------|
| Biguanides | Metformin | First-line; GI side effects |
| Sulfonylureas | Glipizide, Gliclazide, Glimepiride | Risk of hypoglycemia |
| DPP-4 Inhibitors | Sitagliptin, Linagliptin, Vildagliptin | Weight neutral |
| SGLT-2 Inhibitors | Empagliflozin, Dapagliflozin, Canagliflozin | Cardiorenal benefits |
| GLP-1 RAs | Liraglutide, Semaglutide, Dulaglutide | Injectable; weight loss |

## Antihypertensives
| Class | Examples |
|-------|----------|
| ACE Inhibitors | Enalapril, Lisinopril, Perindopril |
| ARBs | Losartan, Valsartan, Irbesartan |
| CCBs | Amlodipine, Nifedipine |
| Diuretics | Hydrochlorothiazide, Indapamide |

## Statins
| Intensity | Examples |
|-----------|----------|
| High | Atorvastatin 40-80mg, Rosuvastatin 20-40mg |
| Moderate | Atorvastatin 10-20mg, Rosuvastatin 5-10mg, Simvastatin 20-40mg |
| Low | Simvastatin 10mg, Pravastatin 10-20mg |

---

# APPENDIX C: SOURCE REFERENCES

## Primary Singapore Sources
1. MOH Clinical Practice Guidelines on Diabetes Mellitus (2014)
2. MOH Clinical Practice Guidelines on Hypertension (2017)
3. MOH Clinical Practice Guidelines on Lipids (2016)
4. Agency for Care Effectiveness (ACE) Clinical Guidance on Type 2 Diabetes Mellitus: Personalising Management with Non-Insulin Medications (May 2023)
5. ACE Clinical Guidance on Hypertension: Tailoring the Management Plan (December 2023)
6. ACE Clinical Guidance on Lipid Management: Focus on Cardiovascular Risk (December 2023)
7. ACE Clinical Guidance on Foot Assessment in Patients with Diabetes Mellitus (August 2024)
8. MOH National Population Health Survey 2024
9. MOH National Population Health Survey 2022
10. Health Promotion Board Singapore Physical Activity Guidelines (2022)
11. MOH Healthier SG Care Protocols (2024)
12. Academy of Medicine Singapore CPG on Lipid Management (December 2023)
13. CDMP Handbook for Healthcare Professionals (2024)

## Healthcare Institutions
- Singapore General Hospital
- National University Hospital
- Tan Tock Seng Hospital
- Changi General Hospital
- Singapore National Eye Centre
- National Kidney Foundation Singapore
- SingHealth Duke-NUS Diabetes Centre
- National Healthcare Group Eye Institute

## International Guidelines Referenced
- KDIGO 2022 Clinical Practice Guidelines for Diabetes Management in CKD
- KDIGO 2024 Clinical Practice Guidelines for CKD Evaluation and Management
- American Diabetes Association Standards of Care 2025
- International Council of Ophthalmology Guidelines for Diabetic Eye Care 2017
- European Society of Cardiology/EASD Guidelines
- International Working Group on the Diabetic Foot (IWGDF) Guidelines 2023

---

**Document End**

*This document is intended for RAG ingestion and should be chunked appropriately for vector database storage. Each section is designed to be semantically coherent for retrieval purposes.*
