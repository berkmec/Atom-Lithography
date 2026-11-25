// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.2-04)
// ============================================================================
// part_id           : S5.2-04
// parent_bom_id     : S5.2
// subsystem         : S5
// part_name         : Tam-aralikli Pirani/soguk-katot vakum olcerler ve RGA (kutle spektrometre)
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-10 mbar
// tolerance         : ±10% basinc
// computed_mass_kg  : 3.33681
// envelope_mm       : 225.800 x 250.700 x 69.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 225.8000;
bbox_y = 250.7000;
bbox_z = 69.5000;

// Part-specific parametric dimensions
rga_max_amu = 200;
p_min_mbar = 1e-11;
len_mm = 225.8;

// Interface / port parameters (mm)
port_chamber_cf40_mate_od = 69.500;
port_chamber_cf40_mate_bore = 38.000;
port_chamber_cf40_mate_pcd = 58.700;
port_chamber_cf40_mate_bolts = 6;

module part_S5_2_04() {
  union() {
    // Chamber-mating CF40 flange
    translate([6.350, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=38.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // CF40 gauge cross X-run
    translate([52.800, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=43.000, h=80.000, center=true);
        cylinder(d=38.000, h=82.000, center=true);
      }
    }
    // Full-range Pirani / Cold-Cathode gauge
    translate([52.800, 87.000, 0.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=44.000, h=68.000, center=true);
    // 200 amu Quadrupole RGA electronics head
    translate([191.800, 0.000, 0.000]) cube([68.000, 56.000, 62.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-173.595, -173.595, 395.000]) rotate([0.000, 0.000, 225.000]) part_S5_2_04();

part_S5_2_04();
