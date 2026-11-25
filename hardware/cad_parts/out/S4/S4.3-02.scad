// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.3-02)
// ============================================================================
// part_id           : S4.3-02
// parent_bom_id     : S4.3
// subsystem         : S4
// part_name         : UHV kaba piezo stick-slip XY adimlama alt-kademesi (±25 mm)
// material          : Invar-36
// temp_stage        : 300 K (UHV)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±50 nm kaba
// computed_mass_kg  : 3.11496
// envelope_mm       : 110.500 x 110.500 x 159.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 110.5000;
bbox_y = 110.5000;
bbox_z = 159.5000;

// Part-specific parametric dimensions
coarse_xy_mm = 96.0;
stroke_xy_mm = 25.0;
pedestal_id_mm = 90.0;
pedestal_od_mm = 104.0;
pedestal_h_mm = 137.0;

// Interface / port parameters (mm)
port_fine_stage_top_mount_bore = 42.000;
port_chamber_bottom_bolt_ring_od = 110.000;
port_chamber_bottom_bolt_ring_bore = 90.000;
port_chamber_bottom_bolt_ring_pcd = 100.000;
port_chamber_bottom_bolt_ring_bolts = 8;

module part_S4_3_02() {
  difference() {
    union() {
      // ±25 mm Ti/ceramic crossed-roller stick-slip XY coarse stage
      translate([0.000, 0.000, 79.750]) cube([96.000, 96.000, 21.500], center=true);
      // Coaxial Invar-36 pedestal (R=45..52 clearing Cryoperm & B-coils)
      translate([0.000, 0.000, 4.000]) {
        difference() {
          cylinder(d=104.000, h=129.000, center=true);
          cylinder(d=90.000, h=131.000, center=true);
        }
      }
      // Bolted chamber-floor pedestal flange
      translate([0.000, 0.000, -65.000]) {
        difference() {
          cylinder(d=110.000, h=8.000, center=true);
          cylinder(d=90.000, h=10.000, center=true);
        }
      }
    }
    // 8x M4 pedestal base bolt circle
    translate([0.000, 0.000, -65.000]) {
      for (i = [0 : 8 - 1])
        rotate([0, 0, i * 360 / 8])
          translate([50.000, 0, 0])
            cylinder(d=4.500, h=12.000, center=true);
    }
    // Ø42 mm central bore
    translate([0.000, 0.000, 79.750]) cylinder(d=42.000, h=26.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -145.000]) rotate([0.000, 0.000, 0.000]) part_S4_3_02();

part_S4_3_02();
