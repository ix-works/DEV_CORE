---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: both
version: 1.0
last-updated: 2026-05-14
status: active
source: NTTDATA/TR ABAP Development Guideline v1.0 (01.02.2026)
---

# NTTDATA ABAP Development Naming Guideline

**Document:** NTT DATA/TR — ABAP Development Guideline and Clean Core Perspective  
**Version:** 1.0 | **Date:** 01.02.2026 | **Author:** NTTDATA

---

> ## ÖNEMLI KURALLAR
>
> - **Yeni package YARATMA = YASAK** (ADR 0005-C, MUST-NOT). Ayrıca mevcut paketlerden hangisinin kullanılacağını **otomatik SEÇME** — kullanıcıya sor (advisory).
> - **Yeni transport request YARATMA = YASAK** (ADR 0005-C, MUST-NOT). Kullanılacak request numarasını **otomatik SEÇME** — kullanıcıya sor (advisory).

---

## Table of Contents

1. [Why Development Guidelines?](#1-why-development-guidelines)
2. [WRICEF Information](#2-wricef-information)
3. [Package Naming Rules](#3-package-naming-rules)
   - 3.1 [Cloud and Classic Package Comparison](#31-cloud-and-classic-package-comparison)
   - 3.2 [Package Hierarchy Tree](#32-package-hierarchy-tree)
   - 3.3 [Package Numbering Rules](#33-package-numbering-rules)
   - 3.4 [Example SD Module Items](#34-example-sd-module-items)
4. [WRICEF Category-Based Naming Conventions](#4-wricef-category-based-naming-conventions)
   - 4.1 [Reports](#41-reports)
   - 4.2 [Interfaces](#42-interfaces)
   - 4.3 [Conversions](#43-conversions)
   - 4.4 [Enhancements](#44-enhancements)
     - 4.4.1 [Views](#441-views)
     - 4.4.2 [Function Groups and Modules](#442-function-groups-and-modules)
     - 4.4.3 [Class and Interfaces](#443-class-and-interfaces)
     - 4.4.4 [Custom Field and Logic](#444-custom-field-and-logic)
     - 4.4.5 [Data Dictionary](#445-data-dictionary)
     - 4.4.6 [Public Cloud Objects](#446-public-cloud-objects)
     - 4.4.7 [Other Objects](#447-other-objects)
   - 4.5 [Forms](#45-forms)
   - 4.6 [Workflows](#46-workflows)
5. [Naming Checklist](#5-naming-checklist)
6. [References](#6-references)

---

## 1. Why Development Guidelines?

This document will help ensure that all applications developed for projects and products are created to a high standard. It includes naming conventions, project development standards, and ATC code check rules to maintain consistency and quality across the development lifecycle.

The document also emphasizes Cloud readiness, ensuring that all developments are compatible with SAP S/4HANA Cloud and RISE with SAP environments. This includes guidelines for using public APIs, event-driven architectures, and side-by-side extensibility to support hybrid and cloud-native scenarios. By following these standards, teams can deliver robust, future-proof applications that align with SAP's strategic direction and enterprise-grade development practices.

### Clean Core Extensibility Levels

| Level | Definition | Technology |
|-------|-----------|------------|
| **Level A** (Cleanest) | Extensions built on-stack with ABAP Cloud or side-by-side on SAP BTP | RAP, CAP, Low-Code/No-Code, Released APIs |
| **Level B** (Clean) | Compliant with SAP recommendations for classic ABAP and Classical APIs | Classic ABAP, Classical APIs |
| **Level C** (Conditional) | Uses SAP internal objects; requires pre-upgrade checks | Arbitrary SAP Objects |
| **Level D** (Not Clean) | Modifications, non-recommended objects, implicit enhancements | Modifications, Implicit Enh. |

---

## 2. WRICEF Information

WRICEF stands for **Reports, Interfaces, Conversions, Enhancements, Forms, and Workflows**. These are the six categories of development work that are commonly carried out in SAP projects.

| Category | Code | Description |
|----------|------|-------------|
| Workflows | W | Automate business processes: approvals, notifications, event triggers |
| Reports | R | Retrieve data from SAP and present it in a user-friendly format |
| Interfaces | I | Transfer data between SAP and external systems (inbound/outbound) |
| Conversions | C | Convert data from legacy or other systems into SAP format |
| Enhancements | E | Add custom functionality not available out of the box |
| Forms | F | Create printed or electronic documents (invoices, POs, shipping docs) |

---

## 3. Package Naming Rules

Package naming should start with **Z** or **Y** for custom objects, and with a namespace prefix for applications developed for library or products. After that, a module abbreviation and a **3-digit numerical package number** must be added consecutively.

### 3.1 Cloud and Classic Package Comparison

| Aspect | Cloud Package (e.g. ZSD001) | Classic Package (e.g. ZSD001_CLC) |
|--------|----------------------------|-----------------------------------|
| Suffix | None (default) | `_CLC` |
| Development Model | ABAP Cloud | Classic ABAP |
| Object Catalog | Released APIs only | All ABAP objects |
| Development Tool | ADT (Eclipse) only | SE80 + ADT (Eclipse) |
| API Compatibility | Cloud-released APIs | All ABAP statements |
| Clean Core Target | Level A | Level B - C - D |
| When to Create | Always (default) | Only when classic object is needed |

### 3.2 Package Hierarchy Tree

```
Z_ROOT
├── ZSD
│   ├── ZSD001              (Cloud)
│   ├── ZSD001_CLC          (Classic)
│   ├── ZSD001              (Cloud)
│   ├── ZSD001_CLC          (Classic)
│   └── ZSD001              (Cloud)
├── ZMM
│   ├── ZMM001              (Cloud)
│   └── ZMM002              (Cloud)
├── ZFI
├── ZCO
├── ZPP
└── ZHR
```

| Type | Package | Description |
|------|---------|-------------|
| Root | `Z_ROOT` | Root main package for all developments |
| Module | `ZSD` | Module main package |
| Cloud | `ZSD001` | Item development cloud package (sequential) |
| Classic | `ZSD001_CLC` | Development classic package (only when needed) |

### 3.3 Package Numbering Rules

| Rule | Description |
|------|-------------|
| No Underscore Before Number | Number directly follows module code: `ZSD001`, not `ZSD_001` |
| Cloud-First Default | All packages are cloud dev packages by default. No suffix needed. |
| `_CLC` for Classic Only | Create a `_CLC` package only when a classic object is required: `ZSD001_CLC` |
| Number Matching | Classic package shares the same number: `ZSD001` → `ZSD001_CLC` |

> **Key Rule:** The package number (001, 002, 003...) is purely sequential and does **not** indicate WRICEF type.  
> **Important:** `_CLC` package shares the same number as its default counterpart and is only created when classic objects are required for that WRICEF item.

### 3.4 Example SD Module Items

| Package | Description (in Package Definition) |
|---------|--------------------------------------|
| `ZSD001` | Sales Order custom field extension |
| `ZSD001_CLC` | Sales Order classic enhancement impl. |
| `ZSD001` | Sales Order approval monitoring report |
| `ZSD001_CLC` | Sales Order for BAPI usage |
| `ZSD001` | Sales Order confirmation PDF output |
| `ZSD001` | Sales Order approval workflow |

---

## 4. WRICEF Category-Based Naming Conventions

### 4.1 Reports

> **Note:** Report programs and includes are classic objects. They must be placed in `_CLC` packages (e.g., `ZSD001_CLC`).

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Program Report | Z or Y | `P` / `R` | `ZSD001_P_INVOICE_REPORT` | RAP |
| Include | Z or Y | `I` | `ZMM001_I_INVOICE_REPORT` | RAP |

> **Klasik program include türetme (C-INC-NAME-01 · WIRED: `check_package_naming`):** Klasik
> report/module-pool include adı **program adından TÜRETİLİR — kısaltma YOK.** Program
> `Z<n>_P_<BASE>` → include `Z<n>_I_<BASE>_<SUFFIX>` (SUFFIX = `_T01`/`_S01`/`_C01`/`_O01`/`_I01`/`_F01`…).
> Örnek: `ZSD001_P_INVOICE_REPORT` → `ZSD001_I_INVOICE_REPORT_T01` (`ZSD001_I_INVREP_T01` YASAK — kısaltma).
> **Program `_P_` adı ≤ 26 karakter** (include = 26 + `_T01`(4) = 30 ADT obje-adı limitine sığsın).
> Exit/enhancement include'ları (standart programa gömülü, ör. `MV50AFZZ` içeriği) bu türetme
> kuralından muaftır (Z-programdan türemez). Standart-öncesi legacy kısaltmalar proje-lokal
> `include_naming_exempt` (project.yaml) ile grandfather'lanır — rename edilince listeden silinir.

### 4.2 Interfaces

> **Note:** For Service Binding objects, the suffix `_O2` or `_O4` must be added to indicate the OData version (e.g., `ZMM001_UI_DESCRIPTION_O2`, `ZMM001_API_DESCRIPTION_O4`).

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| OData Services | Z or Y | `ODS` | `ZSD001_ODS_CUSTOMER` | RAP |
| Service Definition | Z or Y | `UI` / `API` | `ZMM001_UI_DESCRIPTION` / `ZMM001_API_DESCRIPTION` | Yes |
| Service Binding | Z or Y | `UI` / `API` | `ZMM001_UI_DESCRIPTION_O2` / `ZMM001_API_DESCRIPTION_O2` | Yes |
| Service Consumption | Z or Y | `SC` | `ZMM001_SC_DESCRIPTION` | Yes |
| Inbound / Outbound Service | Z or Y | `IS` / `OS` | `ZMM001_IS_DESCRIPTION` / `ZMM001_OS_DESCRIPTION` | Yes |

### 4.3 Conversions

The project team uploads data into the SAP system using data migration tools such as BDC, LSMW, LTMC, etc. Client and technical teams work with the functional consultant to write programs that read data from those files.

### 4.4 Enhancements

#### 4.4.1 Views

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Projection View | Z or Y | `C` | `ZSD001_C_ORDER` | Yes |
| Interface View | Z or Y | `I` | `ZSD001_I_ORDER` | Yes |
| Extension View | Z or Y | `E` | `ZSD001_E_ORDER` | Yes |
| Root View | Z or Y | `R` | `ZSD001_R_ORDER` | Yes |

#### 4.4.2 Function Groups and Modules

> **Note:** Function Groups and Function Modules are classic ABAP objects and are **NOT cloud-ready**. They must be placed in `_CLC` packages. For cloud development, use ABAP classes with released APIs or RAP-based service implementations instead.

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Function Group | Z or Y | `FG` | `ZSD001_FG_INVOICE` | Wrap In Class |
| Function Module | Z or Y | `FM` | `ZMM001_FM_INVOICE_Z001_OUTPUT` | Wrap In Class |

#### 4.4.3 Class and Interfaces

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Class | Z or Y | `CL` | `ZCL_MM001_DESCRIPTION` | Yes |
| Interface | Z or Y | `IF` | `ZIF_MM001_INVOICE_Z001_OUTPUT` | Yes |
| Exception Class | Z or Y | `CX` | `ZCX_MM001_PO_ERROR` | Yes |
| Test Class | Z or Y | `TC` | `ZCL_MM001_TC_PO_TEST` | Yes |

> **Tüm sınıf rolleri tek desen (proje kararı 2026-06-09):** İş mantığı/utility sınıfı **ve** RAP behavior implementation sınıfı aynı kanonik formu kullanır → **`ZCL_<MODÜL><NNN>_<ad>`** (ör. `ZCL_SD001_SO_MANAGER`, `ZCL_SD001_ORDER`). Geçmişte bazı paketlerde L4 `.rules.md` "iş mantığı class" için `ZSD<NNN>_CL_*` kullanıyordu — bu **LEGACY**, yeni objede kullanılmaz; mevcutların rename'i ertelendi (`governance/deferred-triggers.md`). RAP detayı: `05-coding-rap.md` §4.

#### 4.4.4 Custom Field and Logic

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Custom Fields | Z or Y | `ZZ1_` | `ZZ1_DESC` | Yes |
| Enhancement Impl. | Z or Y | `ENH` | `ZSD001_ENH_MV45AFZZ` | Only In Custom |
| Customer Exits (SMOD/CMOD) | Z or Y | `Z...` | `ZSD001_...` (Include) | Custom Logic |
| Custom Logic | Z or Y | `INCL` | `ZZ1_LE_SHIP_MODIFY_ITEM` | Yes |
| BAdI Implementation | Z or Y | `IMP` | `ZZ1_IMP_PO_CUST` | Custom Logic |
| Customizing Include (EEW*, CI_*) | Z or Y | `ZZ_` | `ZZ_...` (DESC) | Custom Fields |

#### 4.4.5 Data Dictionary

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Table | Z or Y | `T` | `ZMM001_T_DESC` | Yes |
| Draft DB Table | Z or Y | `A` | `ZSD001_A_DESC_D` | Yes |
| Table Type | Z or Y | `TT` | `ZMM001_TT_INVOICE` | Yes |
| Structure | Z or Y | `S` | `ZPP001_S_REPORT` | Yes |
| Append Structure | Z or Y | `ZZ` | `ZZMARA` | Custom Field |
| View | Z or Y | `V` | `ZFI001_CLC_V_SIZE` | CDS View (A) |
| Data Element | Z or Y | `E` | `ZMM001_E_AMOUNT` | Yes |
| Domain | Z or Y | `D` | `ZSD001_D_AMOUNT` | Yes |
| Search Help | Z or Y | `SH` | `ZSD001_CLC_SH_CUSTOMER` | CDS View |
| Message Class | Z or Y | `MC` | `ZSD001_MC` | Yes |
| Number Range | Z or Y | `NR` | `ZSD001_NR` | Yes |
| Transaction Code | Z or Y | `007` | `ZSD001` | No |
| Data Definition | Z or Y | `DDL` | `ZSD001_DDL_CUSTOMER_LIST` | Yes |
| Authorization Object | Z or Y | `Aut` | `Z_PORGIN` | Yes |

#### 4.4.6 Public Cloud Objects

**Communication Objects:**

| Object | Prefix | Object Prefix | Sample |
|--------|--------|---------------|--------|
| Communication Scenario | Z or Y | `CS` | `ZSD001_CS_SALES` |
| Communication System | Z or Y | `CSYS` | `ZSD001_CSYS_EXTSYS` |
| Communication Arrangement | Z or Y | `CARR` | `ZSD001_CARR_SALES` |
| Communication User | Z or Y | `CUSR` | `ZSD001_CUSR_INT` |

**Authorization / App Objects:**

| Object | Prefix | Object Prefix | Sample |
|--------|--------|---------------|--------|
| Business Catalog | Z or Y | `BC` | `ZSD001_BC_SALES` |
| Business Role | Z or Y | `BR` | `ZSD001_BR_SALESREP` |
| App Job Catalog | Z or Y | `AJC` | `ZSD001_AJC_BILLING` |
| App Job Template | Z or Y | `AJT` | `ZSD001_AJT_BILLING` |
| IAM App | Z or Y | `IAM` | `ZSD001_IAM_PORTAL` |

#### 4.4.7 Other Objects

_(No specific naming entries beyond the tables above for this category.)_

### 4.5 Forms

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Smart Form | Z or Y | `SF` | `ZSD001_SF_INVOICE` | Adobe Form |
| Smart Style | Z or Y | `SS` | `ZSD001_SS_INVOICE` | Adobe Form |
| Adobe Form | Z or Y | `AF` | `ZSD001_AF_INVOICE` | Yes |
| Adobe Interface | Z or Y | `IF` | `ZSD001_IF_INVOICE` | Yes |

### 4.6 Workflows

| Object | Prefix | Object Prefix | Sample | Cloud Ready / Alternatives |
|--------|--------|---------------|--------|---------------------------|
| Workflow Template (Abbreviation) | Z or Y | `WF` | `ZSD001_WF_01` | BTP Build Process Automation |
| Workflow Task (Abbreviation) | Z or Y | `TS` | `ZSD001_TS_01` | BTP Build Process Automation |
| Responsibility Rule | Z or Y | `RL` | `ZSD001_RL_01` | BTP Build Process Automation |
| Email Template | Z or Y | `EMT` | `ZSD001_EMT_NOTIFICATION` / `ZSD001_EMT_INFORMATION` | BTP Build Process Automation |

---

## 5. Naming Checklist

| # | Check Item | Example |
|---|-----------|---------|
| ✔ | Z prefix used? | `ZSD001_C_ORDER` |
| ✔ | Module code correct? (MM, SD, FI, CO...) | `ZSD...`, `ZMM...`, `ZFI...` |
| ✔ | Package number sequential and without underscore? | `ZSD001`, `ZSD001` (not `ZSD_001`) |
| ✔ | Object type prefix correct? | `CL`, `IF`, `T`, `S`, `C`, `I`, `R`, `E` |
| ✔ | Descriptive **technical name** in English? (label/title/description ise TR — ADR 0005-D; çelişki yok, kapsam farkı) | `ZCL_SD001_ORDER_HANDLER` |
| ✔ | CDS view prefix correct? | `I_` (Interface), `C_` (Projection), `R_` (Root), `E_` (Extension) |
| ✔ | Classic objects in `_CLC` package only? | Report `ZSD001_CLC_P_...` in `ZSD001_CLC` |
| ✔ | Clean Core level evaluated and documented? | Level A / B / C / D noted |

---

## 5B. Alan Tipleme Önceliği + Reuse Gate (CBO brownfield — gap-analysis #3)

Yeni bir alan/obje tiplerken **bu sırayı izle** (yeni yaratmadan önce mevcudu ara):

1. **Standart DE** (released, Clean Core) varsa onu kullan.
2. **Mevcut Z/CBO DE** (paket veya ortak `ZSD000_*`) varsa onu kullan (duplicate yaratma).
3. Yoksa **yeni Z DE** yarat (TR text, ADR 0005-D).
4. Son çare **primitive** (char/numc...) — tercih edilmez.

**Reuse-first kuralı:** Yeni DTEL/domain/struct/CDS yaratmadan önce, aynı işi gören Z
obje var mı kontrol et. Ortak master/value-help için **ASLA local kopya yaratma** —
`ZSD000_I_*` expose + association kullan (ADR 0009).

> Reviewer: `check_reuse_gate.py` (WARNING) repo-local duplicate + ortak-VH reuse'unu
> SAP'ye yazmadan yakalar. Tam DDIC reuse için canlı `adt_search_objects` (gelecek).

## 6. References

- https://sap.github.io/abap-atc-cr-cv-s4hc/?objectTypes=TABL&q=mara
- https://community.sap.com/t5/technology-blog-posts-by-sap/business-excellence-with-sap-s-new-clean-core-extensibility-levels-why-what/ba-p/14191481
- https://www.sap.com/documents/2024/09/20aece06-d87e-0010-bca6-c68f7e60039b.html
- https://www.sap.com/assetdetail/2023/11/32d4f303-977e-0010-bca6-c68f7e60039b.html
- https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-members/what-is-ricefw/ba-p/13548769
- https://community.sap.com/t5/sap-for-utilities-blog-posts/sap-s-4hana-2023-fps3-what-s-in-it-for-the-utilities-industry/ba-p/13991664
- https://community.sap.com/t5/technology-blog-posts-by-sap/abap-extensibility-guide-clean-core-for-sap-s-4hana-cloud-august-2025/ba-p/14175399
- https://community.sap.com/t5/technology-blog-posts-by-members/clean-core-strategy-a-practical-approach-to-get-a-cleaner-on-premise-system/ba-p/14180311
