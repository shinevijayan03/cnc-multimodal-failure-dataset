# Dataset Download and Staging Proposal

## Purpose

This file proposes the exact datasets and local folder locations to use for the next pipeline step. It is based on:

- `docs/recipe_a_overview.md`
- `config/dataset.yaml`
- the implemented ETL readers in `src/etl`
- current Stage A findings under `docs/refactor_ecosystem`
- verified public dataset/source pages checked on 2026-06-20

After this proposal is reviewed, the next step should wait until the datasets are downloaded and placed in the folders below.

## Core Interpretation

Recipe A needs three modalities:

1. Real sensor data as the temporal anchor.
2. Video clips matched heuristically by machining regime and condition.
3. SOP and maintenance text chunks matched heuristically by topic.

The current code can already process:

- CSV sensor files with columns that map to `x`, `y`, `z` under `data_raw/kaggle_cnc`.
- Markdown, text, DOCX, and PDF manuals under `data_raw/text_manuals` if dependencies are installed.
- MP4 files under `data_raw/video_raw`, with human labels in `video_tags.csv`.

The most practical first build should therefore use the CSV CNC machining dataset first, plus a small curated text and video corpus. Larger lifecycle datasets should be kept as Phase 2/Phase 3 expansion material.

## Recommendation Summary

| Priority | Dataset/Source | Modality | Download Now? | Local Folder | Why |
|---|---|---|---|---|---|
| P0 | Kaggle CNC Machining Data | Sensor | Yes | `data_raw/kaggle_cnc/` | Best match for current `generic_csv` reader and config |
| P0 | Haas mill/operator/service documentation, re-authored or approved for local ingest | Text | Yes | `data_raw/text_manuals/` | Gives SOP and maintenance chunks for assembly |
| P0 | Own CNC/router videos plus Pexels/Pixabay CNC clips | Video | Yes | `data_raw/video_raw/` | Fills visual evidence layer expected by Recipe A |
| P1 | Bosch CNC Machining GitHub/UCI H5 dataset | Sensor | Download after review or keep as secondary | `data_raw/bosch_cnc/` | Strong canonical dataset, but current Bosch reader/config needs validation before relying on it |
| P2 | CNC Mill Tool Wear SMART/Kaggle | Labels/reference | Optional later | `data_raw/cnc_mill_tool_wear/` | Useful label/context source, but current config disables it |
| P2 | QIT-CEMC / Nature full lifecycle milling datasets | Sensor expansion | Optional later | `data_raw/milling_lifecycle/` or separate subfolder | Large and valuable, but not plug-and-play for current readers |

## P0 Dataset 1: Kaggle CNC Machining Data

### Source

- Kaggle dataset: `maximilianfellhuber/cnc-machining-data`
- URL: https://www.kaggle.com/datasets/maximilianfellhuber/cnc-machining-data

### Why This Is First

This dataset matches the current `kaggle_cnc` config:

```yaml
- name: kaggle_cnc
  enabled: true
  path: data_raw/kaggle_cnc
  reader: generic_csv
  fs_hz: 2000
  column_map: { x: ax, y: ay, z: az }
```

The public Kaggle page describes machine folders such as `M01`, `M02`, `M03`, process folders `OP00` to `OP14`, and health labels `good` / `bad`. That is exactly the folder pattern the existing config comment expects.

### Local Folder

Put the extracted dataset contents here:

```text
data_raw/
  kaggle_cnc/
    M01/
      OP00/
        good/
          *.csv
        bad/
          *.csv
      OP01/
      ...
    M02/
    M03/
```

If the downloaded zip extracts into an extra wrapper folder, move the `M01`, `M02`, and `M03` folders directly under:

```text
data_raw/kaggle_cnc/
```

### Download Command Option

If Kaggle CLI is configured:

```bash
kaggle datasets download -d maximilianfellhuber/cnc-machining-data -p data_raw/kaggle_cnc --unzip
```

If downloading manually from the browser, unzip and then ensure this exists:

```text
data_raw/kaggle_cnc/M01/
data_raw/kaggle_cnc/M02/
data_raw/kaggle_cnc/M03/
```

### Acceptance Check

Before proceeding, confirm:

- `data_raw/kaggle_cnc/M01` exists.
- There are nested `OPxx` folders.
- There are nested `good` and/or `bad` folders.
- CSV files contain vibration columns compatible with `x`, `y`, `z` or similar lowercase names.

## P0 Dataset 2: Text Corpus for SOP and Maintenance Evidence

### Sources

Use public manuals and maintenance pages as references, but keep licensing in mind. The safest thesis approach is to re-author concise SOP and maintenance Markdown from those references rather than redistributing copied manual text.

Recommended source references:

- Haas Operator's Manual page: https://www.haascnc.com/owners/Service/operators-manual.html
- Haas Mill Operator Manual PDF, 2024: https://www.haascnc.com/content/dam/haascnc/en/service/manual/operator/english---mill-ngc---operator%27s-manual---2024.pdf
- Haas Service and Support: https://www.haascnc.com/service.html
- Haas Preventive Maintenance: https://www.haascnc.com/service/Preventive_Maintenance.html

### Local Folder

For immediate pipeline ingestion, place only the text files you want the ETL to ingest under:

```text
data_raw/
  text_manuals/
    sop/
      cnc_mill_basic_operation_sop.md
      cnc_router_cutting_sop.md
      safe_setup_and_workholding_sop.md
    maintenance/
      spindle_and_tooling_maintenance.md
      coolant_and_lubrication_maintenance.md
      vibration_chatter_troubleshooting.md
      clamping_fixture_troubleshooting.md
    SOURCES.md
```

### Important Licensing/Quality Note

Do not place raw copyrighted reference PDFs under `data_raw/text_manuals` unless you intentionally want the ETL to ingest them and you are comfortable with the license. If you download PDFs only for reference, keep them outside the text ETL root, for example:

```text
data_raw/
  _reference_only/
    text_sources_do_not_ingest/
      haas_mill_operator_manual_2024.pdf
      haas_preventive_maintenance_page.html
```

### Minimum Content Target for First Build

Create or stage at least:

- 3 SOP Markdown files
- 4 maintenance/troubleshooting Markdown files
- Each file should mention relevant topics such as vibration, chatter, tool wear, coolant, spindle, feed rate, clamping, fixture, workholding, runout, lubrication, and overheating.

This gives the current `TopicTagger` enough keywords to attach SOP and maintenance chunks to incidents.

### Acceptance Check

Before proceeding, confirm:

- `data_raw/text_manuals/sop/*.md` exists.
- `data_raw/text_manuals/maintenance/*.md` exists.
- `data_raw/text_manuals/SOURCES.md` lists the source URLs used.
- Text files are allowed for local research use and are either original/re-authored or license-approved.

## P0 Dataset 3: Video Corpus for Visual Evidence

### Sources

Best sources for first build:

1. Your own CNC/router/mill recordings.
2. Pexels CNC machine/machining videos.
3. Pixabay CNC machining videos.
4. Wikimedia Commons freely licensed CNC/machine videos, where relevant.

Useful starting URLs:

- Pexels CNC machine videos: https://www.pexels.com/search/videos/cnc%20machine/
- Pexels CNC machining videos: https://www.pexels.com/search/videos/cnc%20machining/
- Pexels license: https://www.pexels.com/license/
- Pixabay CNC machining videos: https://pixabay.com/videos/search/cnc%20machining%20company/
- Pixabay license summary: https://pixabay.com/service/license-summary/
- Wikimedia CNC media: https://commons.wikimedia.org/wiki/CNC

### Local Folder

Put raw MP4 files here:

```text
data_raw/
  video_raw/
    own_recordings/
      own_roughing_001.mp4
      own_finishing_001.mp4
      own_idle_setup_001.mp4
    pexels_cnc/
      pexels_cnc_001.mp4
      pexels_cnc_002.mp4
    pixabay_cnc/
      pixabay_cnc_001.mp4
    video_tags.csv
    SOURCES.md
```

### Minimum First-Build Target

For a first working build, collect:

- 20 to 50 clips total.
- Each clip should be 5 to 30 seconds before ETL; the current config expects 5 to 10 seconds after normalization/selection.
- Prefer clips showing actual cutting, spindle movement, coolant, setup/idle, tool changes, or visible vibration/chatter.

For thesis-scale work, the longer-term target remains around 1,000 normalized clips.

### Required `video_tags.csv`

Create:

```text
data_raw/video_raw/video_tags.csv
```

Minimum columns accepted by current code:

```csv
file,regime,condition,source,source_url,license,notes
own_recordings/own_roughing_001.mp4,roughing,normal,own,local_recording,own,author recorded
own_recordings/own_idle_setup_001.mp4,idle,normal,own,local_recording,own,setup or non-cutting clip
pexels_cnc/pexels_cnc_001.mp4,finishing,normal,pexels,https://www.pexels.com/...,pexels_license,downloaded for local research
pixabay_cnc/pixabay_cnc_001.mp4,drilling,normal,pixabay,https://pixabay.com/...,pixabay_license,downloaded for local research
```

Allowed `regime` values from config:

```text
roughing, finishing, plunge, idle, drilling, contouring
```

Allowed `condition` values from config:

```text
normal, tool_wear_visible, heavy_vibration, coolant_issue, chatter, chip_packing
```

### Acceptance Check

Before proceeding, confirm:

- `data_raw/video_raw/**/*.mp4` contains at least 20 clips.
- `data_raw/video_raw/video_tags.csv` exists.
- Every clip has a row in `video_tags.csv`.
- `SOURCES.md` lists each external clip URL and license.
- `ffmpeg` is installed before expecting video normalization to run.

## P1 Dataset: Bosch CNC Machining H5 Dataset

### Sources

- UCI page: https://archive.ics.uci.edu/dataset/752/bosch%2Bcnc%2Bmachining%2Bdataset
- GitHub source: https://github.com/boschresearch/CNC_Machining

### Why It Is Valuable

The Bosch/UCI dataset is a real industrial CNC milling vibration dataset. The UCI page describes it as multivariate time-series data with 2700 instances and 3 features. The Bosch GitHub README says the data were collected from three CNC milling machines, 15 processes, and `good` / `bad` labels, with tri-axial acceleration sampled at 2 kHz.

### Why It Is Not P0

The current config has:

```yaml
reader: bosch_h5
column_map: { ax: X, ay: Y, az: Z }
```

But the implemented Bosch reader creates lowercase `x`, `y`, `z` columns. That means the reader/config should be validated or patched before this dataset becomes the main ETL input.

### Local Folder

If you download it now, keep it here:

```text
data_raw/
  bosch_cnc/
    M01/
      OP00/
        good/
          *.h5
        bad/
          *.h5
    M02/
    M03/
```

### Acceptance Check

Before enabling this as a main dataset, confirm:

- H5 files are present under `data_raw/bosch_cnc`.
- A sample H5 file can be opened with `h5py`.
- The dataset key inside H5 matches the reader or can be patched.
- Axis columns are mapped to `ax`, `ay`, `az`.

## P2 Dataset: CNC Mill Tool Wear SMART/Kaggle

### Sources

- Kaggle dataset linked from the industrial datasets index: https://www.kaggle.com/datasets/shasun/tool-wear-detection-in-cnc-mill
- Documentation mirror: https://github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/CNC%20Mill%20Tool%20Wear/README.md

### Why Keep It

This dataset is useful for tool wear, feed rate, and clamping context. The documentation describes 18 machining experiments, `train.csv`, and `experiment_01.csv` through `experiment_18.csv` time series at 100 ms sampling.

### Why It Is Optional

The current project config disables this dataset because it is not directly compatible with the RMS windowing path as configured.

### Local Folder

```text
data_raw/
  cnc_mill_tool_wear/
    train.csv
    experiment_01.csv
    experiment_02.csv
    ...
    experiment_18.csv
```

### Use

Keep as a future label/reference dataset. Do not enable it until the reader and column mapping are explicitly designed.

## P2 Dataset: Full Lifecycle Milling Datasets

### Candidate Sources

- QIT-CEMC coated end milling cutter tool wear whole life cycle: https://www.nature.com/articles/s41597-024-04345-2
- QIT-CEMC raw data DOI: https://doi.org/10.6084/m9.figshare.27323346
- New open milling process dataset for classification and tool-life estimation: https://www.nature.com/articles/s41597-025-04923-y

### Why Keep Them

These are valuable for future scale, tool-life regression/classification, and richer multi-sensor evidence. QIT-CEMC includes vibration, sound, cutting force, torque, and wear measurements.

### Why Not First

They are large and not plug-and-play for the current `generic_csv` or `bosch_h5` readers. They should be treated as Stage B/Stage C expansion datasets.

### Local Folder

Use one of these after approval:

```text
data_raw/
  milling_lifecycle/
    qit_cemc/
      raw/
      metadata/
    open_milling_process_2025/
      raw/
      metadata/
```

Do not enable in `config/dataset.yaml` until a reader is designed.

## Final Proposed First-Build Folder Tree

Create or populate this tree first:

```text
data_raw/
  kaggle_cnc/
    M01/
    M02/
    M03/

  text_manuals/
    sop/
      cnc_mill_basic_operation_sop.md
      cnc_router_cutting_sop.md
      safe_setup_and_workholding_sop.md
    maintenance/
      spindle_and_tooling_maintenance.md
      coolant_and_lubrication_maintenance.md
      vibration_chatter_troubleshooting.md
      clamping_fixture_troubleshooting.md
    SOURCES.md

  video_raw/
    own_recordings/
    pexels_cnc/
    pixabay_cnc/
    video_tags.csv
    SOURCES.md

  _reference_only/
    text_sources_do_not_ingest/
    dataset_download_notes/
```

Optional later:

```text
data_raw/
  bosch_cnc/
  cnc_mill_tool_wear/
  milling_lifecycle/
```

## PowerShell Folder Creation Commands

Run these from the repository root if you want the folders created before download:

```powershell
New-Item -ItemType Directory -Force -Path `
  data_raw\kaggle_cnc, `
  data_raw\text_manuals\sop, `
  data_raw\text_manuals\maintenance, `
  data_raw\video_raw\own_recordings, `
  data_raw\video_raw\pexels_cnc, `
  data_raw\video_raw\pixabay_cnc, `
  data_raw\_reference_only\text_sources_do_not_ingest, `
  data_raw\_reference_only\dataset_download_notes | Out-Null
```

## Review and Confirmation Checklist

Please review and confirm:

- [ ] You approve P0 downloads: Kaggle CNC CSV, text corpus, and video corpus.
- [ ] You want Bosch H5 downloaded now or deferred until the reader/config is fixed.
- [ ] You want CNC Mill Tool Wear downloaded now or deferred.
- [ ] You want full lifecycle datasets downloaded now or deferred.
- [ ] You have downloaded and staged `data_raw/kaggle_cnc`.
- [ ] You have staged text files under `data_raw/text_manuals`.
- [ ] You have staged videos and `video_tags.csv` under `data_raw/video_raw`.
- [ ] You have installed `ffmpeg` if video ETL should run.
- [ ] You have installed optional text dependencies if PDFs should be ingested.

## Stop Condition

Do not proceed to the next processing step until the user confirms:

```text
I reviewed the dataset proposal, downloaded the approved files, and placed them in the specified folders.
```

