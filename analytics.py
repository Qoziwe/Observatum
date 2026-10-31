import math
from statistics import mean, median, pstdev
from database import OPTIONS, fetch_all_responses

SHORT_LABELS = {
    "Bukit Jalil / Sri Petaling / Sungai Besi": "Bukit Jalil / Sri Petaling",
    "KL City Centre (KLCC / Bukit Bintang / Cheras)": "KL City Centre (KLCC)",
    "Bangsar / Mid Valley / Brickfields": "Bangsar / Mid Valley",
    "Subang Jaya / Sunway / Petaling Jaya": "Subang / Sunway / PJ",
    "Setapak / Wangsa Maju / Ampang": "Setapak / Wangsa Maju",
    "Cyberjaya / Serdang / Puchong": "Cyberjaya / Serdang",
    "Yes 5G (YTL Communications)": "Yes 5G",
    "Unifi (Telekom Malaysia)": "Unifi Fibre",
    "Campus / Accommodation Shared Wi-Fi": "Campus / Shared Wi-Fi",
    "I only use Mobile Data / Hotspot": "Mobile Hotspot Only",
    "Rarely (Once or twice a month)": "Rarely (1-2x/mo)",
    "Evening peak hours (7:00 PM – 11:00 PM)": "Evening Peak (7–11 PM)",
    "Daytime work/study hours (9:00 AM – 5:00 PM)": "Daytime (9 AM–5 PM)",
    "During heavy rain / bad weather in KL": "Heavy Rain / Weather",
    "Inside high-rise buildings (Condominiums, malls, campus blocks)": "High-Rise Indoors",
    "While commuting (LRT/MRT/Highways)": "Commuting (LRT/MRT)",
    "Academic tasks (Accessing Moodle/Teams, submitting assignments, online classes)": "Academic (Moodle/Teams)",
    "Digital payments & E-Wallets (Failing to load QR codes/Touch ’n Go at checkout counters)": "QR / E-Wallet Payments",
    "Transport & Navigation (Booking Grab, loading Google Maps/Waze)": "Grab / Maps / Waze",
    "Video/Voice calls with family, friends, or teammates (Lagging, robotic voice, dropping out)": "Video & Voice Calls",
    "Entertainment & Gaming (High ping, buffering streams)": "Gaming & Streaming",
    "Remote work / Cloud collaboration": "Remote / Cloud Work",
    "Switching between Wi-Fi and Mobile Hotspot constantly": "Wi-Fi ↔ Hotspot Toggle",
    "Buying extra mobile data passes / secondary SIM card from another provider": "Extra Data / 2nd SIM",
    "Moving to another physical location (e.g., cafe, library, near a window) just to get a signal": "Relocating for Signal",
    "Restarting the router or toggling Airplane Mode repeatedly": "Router / Airplane Reset",
    "Missing deadlines or delaying urgent tasks": "Missed Deadlines",
    "Very Dissatisfied (Trapped in unhelpful AI chatbot loops, slow resolution)": "Very Dissatisfied (AI Loop)",
    "Dissatisfied (Took too long to fix the issue)": "Dissatisfied (Slow Fix)",
    "Neutral (Issue resolved, but average experience)": "Neutral",
    "Satisfied (Fast and helpful support)": "Satisfied",
    "I have never contacted support because I don’t think they will help": "Never Contacted (No Trust)",
    "Strongly Disagree (I pay for high speed, but get unstable service)": "Strongly Disagree",
    "Yes, definitely! That would solve a major pain point.": "Yes, Definitely",
    "Maybe, depending on how seamlessly it works.": "Maybe (If Seamless)",
    "No, I don’t think it is necessary.": "No, Unnecessary",
    "Real-time outage & tower congestion map inside the app (with exact repair countdowns)": "Live Outage & Tower Map",
    "Faster human customer support (bypassing repetitive AI chatbots during outages)": "Direct Human Support (No AI)",
    "Upgrading indoor building/condominium wiring and signal repeaters": "Indoor Condo Repeaters/Wiring",
    "Automatic bill rebates when network uptime falls below standard": "Auto Bill Rebates on Downtime",
    "Automatic backup eSIM / hotspot data during fiber cuts": "Auto Backup eSIM / Data",
}


def short_label(val: str) -> str:
    return SHORT_LABELS.get(val, val)


def compute_dashboard_payload() -> dict:
    rows = fetch_all_responses()
    total = len(rows)
    demo_count = sum(1 for r in rows if r.get("is_demo") == 1)
    real_count = total - demo_count

    distributions = {}
    for field, opts in OPTIONS.items():
        distributions[field] = {
            "labels": [short_label(o) for o in opts],
            "full_labels": opts,
            "counts": [0 for _ in opts],
        }

    frustration_counts = [0, 0, 0, 0, 0]
    frustration_values = []

    freq_weight = {
        "Multiple times a day": 1.0,
        "Once a day": 0.75,
        "A few times a week": 0.5,
        "Rarely (Once or twice a month)": 0.2,
        "Never": 0.0,
    }
    phantom_weight = {
        "Yes, very frequently": 1.0,
        "Yes, occasionally": 0.65,
        "Rarely": 0.25,
        "No, never": 0.0,
    }
    value_weight = {
        "Strongly Disagree (I pay for high speed, but get unstable service)": 1.0,
        "Disagree": 0.75,
        "Neutral": 0.45,
        "Agree": 0.15,
        "Strongly Agree": 0.0,
    }

    mobile_opts = OPTIONS["q5_mobile_provider"]
    freq_opts = OPTIONS["q7_disconnect_freq"]
    broadband_opts = OPTIONS["q6_broadband_provider"]
    value_opts = OPTIONS["q14_price_value_match"]
    support_opts = OPTIONS["q13_support_satisfaction"]
    area_opts = OPTIONS["q4_area"]

    heatmap_mobile_freq = [[0 for _ in freq_opts] for _ in mobile_opts]
    heatmap_support_value = [[0 for _ in value_opts] for _ in support_opts]
    broadband_vs_value = [[0 for _ in value_opts] for _ in broadband_opts]

    mobile_frustration_map = {m: [] for m in mobile_opts}
    broadband_frustration_map = {b: [] for b in broadband_opts}
    area_stats_map = {
        a: {"count": 0, "frustration": [], "daily_drop": 0, "frequent_phantom": 0, "pain_scores": []}
        for a in area_opts
    }

    sankey_edge_counts = {}
    stories = []
    pain_scores = []

    daily_disconnect_hits = 0
    phantom_hits = 0
    unfair_price_hits = 0
    support_pain_hits = 0
    pitch_definite_hits = 0
    pitch_maybe_hits = 0
    evening_peak_hits = 0

    for r in rows:
        for field in (
            
            "q3_occupation",
            "q4_area",
            "q5_mobile_provider",
            "q6_broadband_provider",
            "q7_disconnect_freq",
            "q8_phantom_signal",
            "q13_support_satisfaction",
            "q14_price_value_match",
            "q15_auto_backup_support",
        ):
            val = r.get(field, "")
            if val in OPTIONS[field]:
                idx = OPTIONS[field].index(val)
                distributions[field]["counts"][idx] += 1

        for mfield in ("q9_worst_conditions", "q11_impacted_activities", "q12_coping_mechanisms", "q16_top_improvements"):
            items = r.get(mfield, []) or []
            for item in items:
                if item in OPTIONS[mfield]:
                    idx = OPTIONS[mfield].index(item)
                    distributions[mfield]["counts"][idx] += 1

        if "Evening peak hours (7:00 PM – 11:00 PM)" in (r.get("q9_worst_conditions") or []):
            evening_peak_hits += 1

        f_val = max(1, min(5, int(r.get("q10_frustration_scale", 3))))
        frustration_counts[f_val - 1] += 1
        frustration_values.append(f_val)

        mob = r.get("q5_mobile_provider", "")
        frq = r.get("q7_disconnect_freq", "")
        brd = r.get("q6_broadband_provider", "")
        val_m = r.get("q14_price_value_match", "")
        sup = r.get("q13_support_satisfaction", "")
        area = r.get("q4_area", "")
        phn = r.get("q8_phantom_signal", "")
        q15 = r.get("q15_auto_backup_support", "")

        if frq in ("Multiple times a day", "Once a day"):
            daily_disconnect_hits += 1
        if phn in ("Yes, very frequently", "Yes, occasionally"):
            phantom_hits += 1
        if val_m in ("Strongly Disagree (I pay for high speed, but get unstable service)", "Disagree"):
            unfair_price_hits += 1
        if sup in (
            "Very Dissatisfied (Trapped in unhelpful AI chatbot loops, slow resolution)",
            "Dissatisfied (Took too long to fix the issue)",
            "I have never contacted support because I don’t think they will help",
        ):
            support_pain_hits += 1
        if q15 == "Yes, definitely! That would solve a major pain point.":
            pitch_definite_hits += 1
        elif q15 == "Maybe, depending on how seamlessly it works.":
            pitch_maybe_hits += 1

        row_pain = (
            0.30 * ((f_val - 1) / 4.0)
            + 0.30 * freq_weight.get(frq, 0.4)
            + 0.20 * phantom_weight.get(phn, 0.4)
            + 0.20 * value_weight.get(val_m, 0.4)
        ) * 100.0
        pain_scores.append(row_pain)

        if mob in mobile_opts and frq in freq_opts:
            heatmap_mobile_freq[mobile_opts.index(mob)][freq_opts.index(frq)] += 1
        if sup in support_opts and val_m in value_opts:
            heatmap_support_value[support_opts.index(sup)][value_opts.index(val_m)] += 1
        if brd in broadband_opts and val_m in value_opts:
            broadband_vs_value[broadband_opts.index(brd)][value_opts.index(val_m)] += 1

        if mob in mobile_frustration_map:
            mobile_frustration_map[mob].append(f_val)
        if brd in broadband_frustration_map:
            broadband_frustration_map[brd].append(f_val)

        if area in area_stats_map:
            st = area_stats_map[area]
            st["count"] += 1
            st["frustration"].append(f_val)
            st["pain_scores"].append(row_pain)
            if frq in ("Multiple times a day", "Once a day"):
                st["daily_drop"] += 1
            if phn in ("Yes, very frequently", "Yes, occasionally"):
                st["frequent_phantom"] += 1

        if area in area_opts and mob in mobile_opts and frq in freq_opts:
            a_node = f"AREA: {short_label(area)}"
            m_node = f"SIM: {short_label(mob)}"
            f_node = f"DROP: {short_label(frq)}"
            sankey_edge_counts[(a_node, m_node)] = sankey_edge_counts.get((a_node, m_node), 0) + 1
            sankey_edge_counts[(m_node, f_node)] = sankey_edge_counts.get((m_node, f_node), 0) + 1

        moment = (r.get("q17_memorable_moment") or "").strip()
        if moment:
            stories.append(
                {
                    "id": r["id"],
                    "receipt_code": r["receipt_code"],
                    "participant_id": r["q1_participant_id"],
                    "area": short_label(area),
                    "mobile": short_label(mob),
                    "broadband": short_label(brd),
                    "frustration": f_val,
                    "text": moment,
                    "created_at": r["created_at"],
                    "is_demo": bool(r.get("is_demo")),
                }
            )

    def pct(n: int) -> float:
        return round((n / total) * 100.0, 1) if total > 0 else 0.0

    mean_frust = round(mean(frustration_values), 2) if frustration_values else 0.0
    med_frust = round(float(median(frustration_values)), 1) if frustration_values else 0.0
    std_frust = round(pstdev(frustration_values), 2) if len(frustration_values) > 1 else 0.0
    high_frust_hits = sum(1 for v in frustration_values if v >= 4)
    composite_pain = round(mean(pain_scores), 1) if pain_scores else 0.0

    heatmap_mf_points = []
    for mi, _ in enumerate(mobile_opts):
        for fi, _ in enumerate(freq_opts):
            heatmap_mf_points.append([fi, mi, heatmap_mobile_freq[mi][fi]])

    heatmap_sv_points = []
    for si, _ in enumerate(support_opts):
        for vi, _ in enumerate(value_opts):
            heatmap_sv_points.append([vi, si, heatmap_support_value[si][vi]])

    mobile_avg_frustration = [
        round(mean(mobile_frustration_map[m]), 2) if mobile_frustration_map[m] else 0.0
        for m in mobile_opts
    ]
    broadband_avg_frustration = [
        round(mean(broadband_frustration_map[b]), 2) if broadband_frustration_map[b] else 0.0
        for b in broadband_opts
    ]

    area_vulnerability = []
    for a in area_opts:
        st = area_stats_map[a]
        cnt = st["count"]
        area_vulnerability.append(
            {
                "area": short_label(a),
                "count": cnt,
                "avg_frustration": round(mean(st["frustration"]), 2) if st["frustration"] else 0.0,
                "daily_drop_pct": round((st["daily_drop"] / cnt) * 100.0, 1) if cnt > 0 else 0.0,
                "phantom_pct": round((st["frequent_phantom"] / cnt) * 100.0, 1) if cnt > 0 else 0.0,
                "pain_index": round(mean(st["pain_scores"]), 1) if st["pain_scores"] else 0.0,
            }
        )

    sankey_nodes_set = []
    for src, dst in sankey_edge_counts:
        if src not in sankey_nodes_set:
            sankey_nodes_set.append(src)
        if dst not in sankey_nodes_set:
            sankey_nodes_set.append(dst)

    sankey_links = [
        {"source": src, "target": dst, "value": val}
        for (src, dst), val in sankey_edge_counts.items()
        if val > 0
    ]

    q9_pairs = list(
        zip(
            distributions["q9_worst_conditions"]["labels"],
            distributions["q9_worst_conditions"]["counts"],
        )
    )
    q9_pairs.sort(key=lambda x: x[1], reverse=True)
    q9_sum = sum(x[1] for x in q9_pairs) or 1
    cum = 0
    q9_pareto = {"labels": [], "counts": [], "cumulative_pct": []}
    for lbl, cnt in q9_pairs:
        cum += cnt
        q9_pareto["labels"].append(lbl)
        q9_pareto["counts"].append(cnt)
        q9_pareto["cumulative_pct"].append(round((cum / q9_sum) * 100.0, 1))

    recent_table = []
    for r in rows[:100]:
        recent_table.append(
            {
                "id": r["id"],
                "receipt_code": r["receipt_code"],
                "created_at": r["created_at"],
                "is_demo": bool(r.get("is_demo")),
                "participant_id": r["q1_participant_id"],
                "occupation": short_label(r["q3_occupation"]),
                "area": short_label(r["q4_area"]),
                "mobile": short_label(r["q5_mobile_provider"]),
                "broadband": short_label(r["q6_broadband_provider"]),
                "disconnect_freq": short_label(r["q7_disconnect_freq"]),
                "phantom_signal": short_label(r["q8_phantom_signal"]),
                "frustration": r["q10_frustration_scale"],
                "price_value": short_label(r["q14_price_value_match"]),
                "pitch_support": short_label(r["q15_auto_backup_support"]),
            }
        )

    return {
        "kpis": {
            "total": total,
            "real_count": real_count,
            "demo_count": demo_count,
            "mean_frustration": mean_frust,
            "median_frustration": med_frust,
            "std_frustration": std_frust,
            "high_frustration_pct": pct(high_frust_hits),
            "daily_disconnect_pct": pct(daily_disconnect_hits),
            "phantom_signal_pct": pct(phantom_hits),
            "evening_peak_pct": pct(evening_peak_hits),
            "unfair_price_pct": pct(unfair_price_hits),
            "support_pain_pct": pct(support_pain_hits),
            "pitch_approval_pct": pct(pitch_definite_hits + pitch_maybe_hits),
            "pitch_definite_pct": pct(pitch_definite_hits),
            "composite_pain_index": composite_pain,
        },
        "frustration_scale": {
            "labels": ["1 — Calm", "2 — Mild", "3 — Moderate", "4 — High", "5 — Extreme"],
            "counts": frustration_counts,
        },
        "distributions": distributions,
        "cross": {
            "heatmap_mobile_freq": {
                "mobile_labels": [short_label(m) for m in mobile_opts],
                "freq_labels": [short_label(f) for f in freq_opts],
                "points": heatmap_mf_points,
                "mobile_avg_frustration": mobile_avg_frustration,
            },
            "heatmap_support_value": {
                "support_labels": [short_label(s) for s in support_opts],
                "value_labels": [short_label(v) for v in value_opts],
                "points": heatmap_sv_points,
            },
            "broadband_vs_value": {
                "broadband_labels": [short_label(b) for b in broadband_opts],
                "value_labels": [short_label(v) for v in value_opts],
                "matrix": broadband_vs_value,
                "broadband_avg_frustration": broadband_avg_frustration,
            },
            "area_vulnerability": area_vulnerability,
            "sankey": {
                "nodes": [{"name": n} for n in sankey_nodes_set],
                "links": sankey_links,
            },
            "q9_pareto": q9_pareto,
        },
        "stories": stories[:40],
        "recent_responses": recent_table,
    }
