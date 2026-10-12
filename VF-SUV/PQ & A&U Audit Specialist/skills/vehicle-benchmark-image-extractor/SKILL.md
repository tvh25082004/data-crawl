---
name: vehicle-benchmark-image-extractor
description: Crawls permitted public automotive websites, prioritizing Autohome, to find, extract, deduplicate, classify, and return traceable vehicle benchmark images for Perceived Quality and Accessibility & Usability assessments. Records each image’s vehicle identity, feature, viewing angle, source page, evidence quality, relevance, and comparability limitations without bypassing access controls or treating photographs as dimensional, tactile, acoustic, or functional proof.
---

# Vehicle Benchmark Extractor

## Purpose

Collect publicly accessible automotive benchmark images and associated metadata for Perceived Quality (PQ) and Accessibility & Usability (A&U) assessments.

Use extracted content only as comparative visual evidence. Do not treat photographs as proof of dimensions, tactile quality, operating effort, sound, comfort, durability, or regulatory compliance.

## When to Use

Use this tool when the user asks to:

- Benchmark a vehicle, component, feature, or design execution.
- Find exterior or interior vehicle images.
- Compare PQ or A&U execution between vehicles.
- Collect visual evidence for an audit report.
- Find matching views for side-by-side comparisons.
- Obtain competitor images for a PowerPoint report.

Do not use this tool when the user has already supplied sufficient images and no external benchmark is requested.

## Required Inputs

Collect or infer the following:

- Manufacturer and model.
- Generation or model year.
- Market or country.
- Variant and trim, when relevant.
- Exterior or interior scope.
- Module, submodule, feature, or component.
- Required viewing angles.
- Benchmark vehicle or segment.
- Maximum number of images.
- Minimum image resolution.
- Preferred source websites.
- Intended PQ or A&U criteria.

Ask for missing information only when it materially affects vehicle identification or benchmark comparability.

## Source Priority

Search sources in this order:

1. `autohome.com.cn`.
2. Official manufacturer and regional product websites.
3. Reputable automotive publications and road-test websites.
4. Established dealer inventory pages with clearly identified vehicles.
5. Other public sources only when stronger sources are unavailable.

Search using Chinese and international vehicle names when applicable.

## Search Procedure

1. Identify the exact vehicle, generation, model year, market, variant, and trim.
2. Create search combinations using:
   - Vehicle name.
   - Chinese vehicle name, when available.
   - Model year.
   - Trim.
   - Module or feature.
   - Required view.
3. Search Autohome first.
4. Locate galleries, comparison articles, reviews, official images, and detailed interior or exterior photographs.
5. If sufficient evidence is unavailable, continue through the source-priority list.
6. Prefer pages that clearly identify the vehicle and contain multiple consistent images.
7. Stop when the requested evidence coverage and maximum image count are reached.

## Image Selection Rules

Select images that:

- Clearly show the requested vehicle or component.
- Match the requested generation, market, trim, and equipment.
- Provide useful resolution and lighting.
- Show the feature without excessive obstruction.
- Support a relevant PQ or A&U criterion.
- Offer comparable framing or viewing angle.
- Retain a traceable source page.

Reject or downgrade images that:

- Cannot be confidently linked to the requested vehicle.
- Show modified, prototype, damaged, or aftermarket vehicles without clear labeling.
- Are heavily edited, rendered, watermarked, cropped, or too small.
- Duplicate another selected image.
- Show a different trim or market without disclosure.
- Contain unrelated people, personal information, or private content.

## Image Extraction

For each selected image:

1. Capture the source-page URL.
2. Capture the direct image URL when access and reuse conditions permit.
3. Record the original filename, file type, pixel dimensions, and file size when available.
4. Download the highest permitted resolution.
5. Generate a stable local filename using:
   `manufacturer_model_year_trim_module_view_sequence`
6. Remove duplicates using:
   - Direct URL.
   - Filename.
   - File hash.
   - Pixel dimensions.
   - Visual similarity.
7. Preserve the original image without altering its content.
8. Create a separate annotated copy only when requested.

## Classification

Assign each image:

- Manufacturer.
- Vehicle model.
- Generation.
- Model year.
- Market.
- Variant or trim.
- Exterior or interior.
- Module.
- Submodule.
- Feature.
- View or camera angle.
- Applicable PQ criteria.
- Applicable A&U criteria.
- Benchmark purpose.

### PQ criteria

- Fit & Finish.
- Aesthetics.
- Touch & Feel.
- Functionality.
- Sound Quality.
- Harmony & Authenticity.

### A&U criteria

- Accessibility / Reach.
- Posture.
- Comfort.
- Space Efficiency.
- Convenience / Usability.
- Intuitiveness.
- Visibility.

## Evidence Quality

Rate evidence quality as:

- **High:** Exact vehicle, year, market, and trim; clear source; suitable resolution; directly shows the requested feature.
- **Medium:** Vehicle and feature are clear, but trim, year, angle, or market differs slightly.
- **Low:** Identification or comparability is uncertain, resolution is weak, or the feature is partially obscured.

Also assign a relevance score from 0–100 based on:

- Vehicle match.
- Feature match.
- View match.
- Image clarity.
- Benchmark comparability.
- Source reliability.

## Comparability Checks

Before recommending an image for comparison, verify:

- Same vehicle segment.
- Comparable market positioning.
- Equivalent feature or component.
- Similar trim level.
- Similar viewing angle and focal distance.
- Comparable lighting and component state.
- Production vehicle status.

State every important mismatch explicitly.

## Required Output

Return a structured image inventory containing:

- Image ID.
- Manufacturer and model.
- Generation and model year.
- Market and trim.
- Module, submodule, and feature.
- Exterior or interior classification.
- View or angle.
- Applicable PQ/A&U criteria.
- Source website.
- Source-page title.
- Source-page URL.
- Direct image URL, when permitted.
- Downloaded filename or file output.
- Image dimensions and format.
- Date accessed.
- Evidence-quality rating.
- Relevance score.
- Comparability limitations.
- Copyright or reuse information when available.
- Extraction status.
- Failure reason when extraction is unsuccessful.

## Summary Output

After processing, provide:

- Number of pages reviewed.
- Number of images found.
- Number of images accepted.
- Number of duplicates removed.
- Number of rejected images.
- Coverage by module, feature, and view.
- Missing benchmark views.
- Recommended images for the audit report.
- Source and comparability limitations.

## Error Handling

- If Autohome has no suitable result, continue with other approved sources.
- If a page blocks automated access, do not bypass the restriction; return the source-page link and status.
- If the vehicle identity is uncertain, label the result as unverified.
- If the direct image cannot be downloaded, retain the source-page URL.
- If only a different trim, market, or model year is available, disclose the mismatch.
- If no reliable image is found, report the missing evidence rather than substituting an unrelated image.
- If rate-limited, pause according to the source requirement and return partial results with status.
- If an image contains personal information, exclude it.



## Automotive Assessment Boundaries

- Do not infer exact gap, flushness, clearance, dimension, or tolerance without scale or measured data.
- Do not score Touch & Feel from images alone.
- Do not score Sound Quality from static images.
- Do not confirm functionality from appearance alone.
- Do not make definitive ergonomic claims without target-user, posture, reach, or dimensional evidence.
- Do not classify a visual benchmark difference as Must Fix solely because a competitor appears better.
- Clearly distinguish observation, inference, and unavailable evidence.

## Completion Criteria

The task is complete when:

- The requested image categories are covered or documented as unavailable.
- Every accepted image has traceable source metadata.
- Duplicate and uncertain images are identified.
- Comparability limitations are recorded.
- The structured inventory and downloadable permitted files are returned.