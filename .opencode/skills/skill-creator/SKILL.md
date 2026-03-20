---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
license: MIT
---

# Skill Creator

This skill provides guidance for creating effective skills.

## About Skills

Skills are modular, self-contained packages that extend Claude's capabilities by providing specialized knowledge, workflows, and tools. Think of them as "onboarding guides" for specific domains or tasks—they transform Claude from a general-purpose agent into a specialized agent equipped with procedural knowledge that no model can fully possess.

### What Skills Provide

1. Specialized workflows - Multi-step procedures for specific domains
2. Tool integrations - Instructions for working with specific file formats or APIs
3. Domain expertise - Company-specific knowledge, schemas, business logic
4. Bundled resources - Scripts, references, and assets for complex and repetitive tasks

## Core Principles

### Concise is Key

The context window is a public good. Skills share the context window with everything else Claude needs: system prompt, conversation history, other Skills' metadata, and the actual user request.

**Default assumption: Claude is already very smart.** Only add context Claude doesn't already have. Challenge each piece of information: "Does Claude really need this explanation?" and "Does this paragraph justify its token cost?"

Prefer concise examples over verbose explanations.

### Set Appropriate Degrees of Freedom

Match the level of specificity to the task's fragility and variability:

**High freedom (text-based instructions)**: Use when multiple approaches are valid, decisions depend on context, or heuristics guide the approach.

**Medium freedom (pseudocode or scripts with parameters)**: Use when a preferred pattern exists, some variation is acceptable, or configuration affects behavior.

**Low freedom (specific scripts, few parameters)**: Use when operations are fragile and error-prone, consistency is critical, or a specific sequence must be followed.

Think of Claude as exploring a path: a narrow bridge with cliffs needs specific guardrails (low freedom), while an open field allows many routes (high freedom).

### Anatomy of a Skill

Every skill consists of a required SKILL.md file and optional bundled resources:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation intended to be loaded into context as needed
    └── assets/           - Files used in output (templates, icons, fonts, etc.)
```

#### SKILL.md (required)

Every SKILL.md consists of:

- **Frontmatter** (YAML): Contains `name` and `description` fields. These are the only fields that Claude reads to determine when the skill gets used, thus it is very important to be clear and comprehensive in describing what the skill is, and when it should be used.
- **Body** (Markdown): Instructions and guidance for using the skill. Only loaded AFTER the skill triggers (if at all).

#### Bundled Resources (optional)

##### Scripts (`scripts/`)

Executable code (Python/Bash/etc.) for tasks that require deterministic reliability or are repeatedly rewritten.

- **When to include**: When the same code is being rewritten repeatedly or deterministic reliability is needed
- **Example**: `scripts/rotate_pdf.py` for PDF rotation tasks
- **Benefits**: Token efficient, deterministic, may be executed without loading into context
- **Note**: Scripts may still need to be read by Claude for patching or environment-specific adjustments

##### References (`references/`)

Documentation and reference material intended to be loaded as needed into context to inform Claude's process and thinking.

- **When to include**: For documentation that Claude should reference while working
- **Examples**: `references/finance.md` for financial schemas, `references/mnda.md` for company NDA template
- **Use cases**: Database schemas, API documentation, domain knowledge, company policies, detailed workflow guides
- **Benefits**: Keeps SKILL.md lean, loaded only when Claude determines it's needed
- **Best practice**: If files are large (>10k words), include grep search patterns in SKILL.md

##### Assets (`assets/`)

Files not intended to be loaded into context, but rather used within the output Claude produces.

- **When to include**: When the skill needs files that will be used in the final output
- **Examples**: `assets/logo.png` for brand assets, `assets/slides.pptx` for PowerPoint templates

#### What to Not Include in a Skill

A skill should only contain essential files that directly support its functionality. Do NOT create extraneous documentation:
- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md

### Progressive Disclosure Design Principle

Skills use a three-level loading system:

1. **Metadata (name + description)** - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed by Claude (scripts can execute without loading into context)

#### Progressive Disclosure Patterns

Keep SKILL.md body under 250 lines. Split content into separate files when approaching this limit.

**Pattern 1: High-level guide with references**

```markdown
## Quick start

Extract text with pdfplumber:
[code example]

## Advanced features

- **Form filling**: See [references/forms.md](references/forms.md)
- **API reference**: See [references/api.md](references/api.md)
```

**Pattern 2: Domain-specific organization**

For Skills with multiple domains:

```
cloud-deploy/
├── SKILL.md (overview and navigation)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

**Pattern 3: Conditional details**

```markdown
## Creating documents

Use docx-js for new documents. See [references/docx-js.md](references/docx-js.md).

**For tracked changes**: See [references/redlining.md](references/redlining.md)
```

## Skill Creation Process

1. Understand the skill with concrete examples
2. Plan reusable skill contents (scripts, references, assets)
3. Initialize the skill (run `init_skill.py`)
4. Edit the skill (implement resources and write SKILL.md)
5. Package the skill (run `package_skill.py`)
6. Iterate based on real usage

### Step 1: Understanding with Concrete Examples

Skip this step only when the skill's usage patterns are already clearly understood.

To create an effective skill, clearly understand concrete examples of how the skill will be used. This understanding can come from either direct user examples or generated examples that are validated with user feedback.

Ask questions like:
- "What functionality should this skill support?"
- "Can you give examples of how this skill would be used?"
- "What would a user say that should trigger this skill?"

### Step 2: Planning the Reusable Skill Contents

Analyze each example to identify what scripts, references, and assets would be helpful:

- **Scripts**: When the same code is being rewritten repeatedly
- **References**: When schemas, policies, or detailed documentation are needed
- **Assets**: When templates, boilerplate, or files are copied to output

### Step 3: Initializing the Skill

When creating a new skill, run the `init_skill.py` script:

```bash
python scripts/init_skill.py <skill-name> --path <output-directory>
```

This creates the skill directory with proper structure.

### Step 4: Edit the Skill

#### Learn Proven Design Patterns

- **Multi-step processes**: See [references/workflows.md](references/workflows.md)
- **Specific output formats**: See [references/output-patterns.md](references/output-patterns.md)

#### Writing Guidelines

##### Frontmatter

```yaml
---
name: my-skill
description: Clear description of what the skill does AND when to use it. Include specific triggers.
---
```

##### Body

Write instructions using imperative/infinitive form.

### Step 5: Packaging a Skill

Once complete, package into a .skill file:

```bash
python scripts/package_skill.py <path/to/skill-folder>
```

The packaging script validates and creates a `.skill` file.

### Step 6: Iterate

After testing:
1. Use the skill on real tasks
2. Notice struggles or inefficiencies
3. Update SKILL.md or bundled resources
4. Test again
