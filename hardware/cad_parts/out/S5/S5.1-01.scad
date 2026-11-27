// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.1-01)
// ============================================================================
// part_id           : S5.1-01
// parent_bom_id     : S5.1
// subsystem         : S5
// part_name         : UHV ana surec odasi (s=0.5 altin zarf, r=175 mm, ~34 L, Exp80)
// material          : 316LN
// temp_stage        : 300 K (150 C bakeout)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.1 mm flans ekseni
// computed_mass_kg  : 80.07578
// envelope_mm       : 539.000 x 500.000 x 408.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 539.0000;
bbox_y = 500.0000;
bbox_z = 408.5000;

// Part-specific parametric dimensions
chamber_r_in_mm = 182.0;
chamber_r_out_mm = 192.0;
inner_vol_L = 34.91;
z_wafer_mm = 500.0;
n_cf_ports = 13;

// Interface / port parameters (mm)
port_bottom_cf400_base_od = 456.000;
port_bottom_cf400_base_bore = 364.000;
port_bottom_cf400_base_pcd = 431.800;
port_bottom_cf400_base_bolts = 40;
port_top_cf400_service_od = 456.000;
port_top_cf400_service_bore = 364.000;
port_top_cf400_service_pcd = 431.800;
port_top_cf400_service_bolts = 40;
port_top_cf250_column_od = 305.000;
port_top_cf250_column_bore = 254.000;
port_top_cf250_column_pcd = 284.200;
port_top_cf250_column_bolts = 32;
port_port_loadlock_pos_x_od = 152.000;
port_port_loadlock_pos_x_bore = 101.600;
port_port_loadlock_pos_x_pcd = 130.200;
port_port_loadlock_pos_x_bolts = 16;
port_port_pump_neg_y_od = 202.500;
port_port_pump_neg_y_bore = 152.400;
port_port_pump_neg_y_pcd = 181.000;
port_port_pump_neg_y_bolts = 20;
port_port_cryo_bridge_neg_x_od = 152.000;
port_port_cryo_bridge_neg_x_bore = 76.000;
port_port_cryo_bridge_neg_x_pcd = 130.200;
port_port_cryo_bridge_neg_x_bolts = 16;
port_port_ibic_ft_45_od = 113.500;
port_port_ibic_ft_45_bore = 63.500;
port_port_ibic_ft_45_pcd = 92.100;
port_port_ibic_ft_45_bolts = 8;
port_port_ibic_ft_315_od = 113.500;
port_port_ibic_ft_315_bore = 63.500;
port_port_ibic_ft_315_pcd = 92.100;
port_port_ibic_ft_315_bolts = 8;
port_port_interf_x_0_od = 69.500;
port_port_interf_x_0_bore = 28.000;
port_port_interf_x_0_pcd = 58.700;
port_port_interf_x_0_bolts = 6;
port_port_interf_y_90_od = 69.500;
port_port_interf_y_90_bore = 28.000;
port_port_interf_y_90_pcd = 58.700;
port_port_interf_y_90_bolts = 6;
port_port_interf_z_270_od = 69.500;
port_port_interf_z_270_bore = 28.000;
port_port_interf_z_270_pcd = 58.700;
port_port_interf_z_270_bolts = 6;
port_port_gauge_rga_225_od = 69.500;
port_port_gauge_rga_225_bore = 38.000;
port_port_gauge_rga_225_pcd = 58.700;
port_port_gauge_rga_225_bolts = 6;
port_port_fiducial_50_od = 69.500;
port_port_fiducial_50_bore = 32.000;
port_port_fiducial_50_pcd = 58.700;
port_port_fiducial_50_bolts = 6;

module part_S5_1_01() {
  difference() {
    union() {
      // Bottom CF400 main flange
      translate([0.000, 0.000, -225.750]) rotate([180.000, 0.000, 0.000]) {
        difference() {
          cylinder(d=456.000, h=28.500, center=true);
          cylinder(d=364.000, h=30.500, center=true);
          translate([0, 0, 12.900]) cylinder(d=420.000, h=1.850);
          for (i = [0 : 40 - 1])
            rotate([0, 0, i * 360 / 40])
              translate([215.900, 0, 0])
                cylinder(d=8.400, h=30.500, center=true);
        }
      }
      // Stepped vacuum baseplate
      translate([0.000, 0.000, -227.750]) cylinder(d=363.200, h=24.500, center=true);
      // 316LN main vessel shell (R_in=182, R_out=192 mm)
      translate([0.000, 0.000, -55.700]) {
        difference() {
          cylinder(d=384.000, h=311.400, center=true);
          cylinder(d=364.000, h=313.400, center=true);
        }
      }
      // Top CF400 service flange
      translate([0.000, 0.000, 114.250]) {
        difference() {
          cylinder(d=456.000, h=28.500, center=true);
          cylinder(d=364.000, h=30.500, center=true);
          translate([0, 0, 12.900]) cylinder(d=420.000, h=1.850);
          for (i = [0 : 40 - 1])
            rotate([0, 0, i * 360 / 40])
              translate([215.900, 0, 0])
                cylinder(d=8.400, h=30.500, center=true);
        }
      }
      // Top CF250 column adapter flange
      translate([0.000, 0.000, 156.250]) {
        difference() {
          cylinder(d=305.000, h=24.500, center=true);
          cylinder(d=254.000, h=26.500, center=true);
          translate([0, 0, 11.000]) cylinder(d=272.900, h=1.750);
          for (i = [0 : 32 - 1])
            rotate([0, 0, i * 360 / 32])
              translate([142.100, 0, 0])
                cylinder(d=8.400, h=26.500, center=true);
        }
      }
      // Welded CF100 radial port port_loadlock_pos_x (0 deg, z_loc=0.0)
      translate([240.100, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=101.600, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // Welded CF150 radial port port_pump_neg_y (270 deg, z_loc=8.0)
      translate([-0.000, -248.900, 8.000]) rotate([0.000, 90.000, 270.000]) {
        difference() {
          cylinder(d=202.500, h=22.200, center=true);
          cylinder(d=152.400, h=24.200, center=true);
          translate([0, 0, 9.850]) cylinder(d=171.300, h=1.750);
          for (i = [0 : 20 - 1])
            rotate([0, 0, i * 360 / 20])
              translate([90.500, 0, 0])
                cylinder(d=8.400, h=24.200, center=true);
        }
      }
      // Welded CF100 radial port port_cryo_bridge_neg_x (180 deg, z_loc=-6.5)
      translate([-279.100, 0.000, -6.500]) rotate([0.000, 90.000, 180.000]) {
        difference() {
          cylinder(d=152.000, h=19.800, center=true);
          cylinder(d=76.000, h=21.800, center=true);
          translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
          for (i = [0 : 16 - 1])
            rotate([0, 0, i * 360 / 16])
              translate([65.100, 0, 0])
                cylinder(d=8.400, h=21.800, center=true);
        }
      }
      // Welded CF63 radial port port_ibic_ft_45 (45 deg, z_loc=-105.0)
      translate([167.054, 167.054, -105.000]) rotate([0.000, 90.000, 45.000]) {
        difference() {
          cylinder(d=113.500, h=17.500, center=true);
          cylinder(d=63.500, h=19.500, center=true);
          translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
          for (i = [0 : 8 - 1])
            rotate([0, 0, i * 360 / 8])
              translate([46.050, 0, 0])
                cylinder(d=8.400, h=19.500, center=true);
        }
      }
      // Welded CF63 radial port port_ibic_ft_315 (315 deg, z_loc=-105.0)
      translate([167.054, -167.054, -105.000]) rotate([0.000, 90.000, 315.000]) {
        difference() {
          cylinder(d=113.500, h=17.500, center=true);
          cylinder(d=63.500, h=19.500, center=true);
          translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
          for (i = [0 : 8 - 1])
            rotate([0, 0, i * 360 / 8])
              translate([46.050, 0, 0])
                cylinder(d=8.400, h=19.500, center=true);
        }
      }
      // Welded CF40 radial port port_interf_x_0 (0 deg, z_loc=-133.0)
      translate([233.650, 0.000, -133.000]) rotate([0.000, 90.000, 0.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=28.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
      // Welded CF40 radial port port_interf_y_90 (90 deg, z_loc=-133.0)
      translate([0.000, 233.650, -133.000]) rotate([0.000, 90.000, 90.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=28.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
      // Welded CF40 radial port port_interf_z_270 (270 deg, z_loc=-133.0)
      translate([-0.000, -233.650, -133.000]) rotate([0.000, 90.000, 270.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=28.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
      // Welded CF40 radial port port_gauge_rga_225 (225 deg, z_loc=-105.0)
      translate([-168.751, -168.751, -105.000]) rotate([0.000, 90.000, 225.000]) {
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
      // Welded CF40 radial port port_fiducial_50 (50 deg, z_loc=9.0)
      translate([150.187, 178.986, 9.000]) rotate([0.000, 90.000, 50.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=32.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
    }
    // Port bore port_loadlock_pos_x
    translate([216.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=101.600, h=72.000, center=true);
    // Port bore port_pump_neg_y
    translate([-0.000, -221.000, 8.000]) rotate([0.000, 90.000, 270.000]) cylinder(d=152.400, h=82.000, center=true);
    // Port bore port_cryo_bridge_neg_x
    translate([-235.500, 0.000, -6.500]) rotate([0.000, 90.000, 180.000]) cylinder(d=76.000, h=111.000, center=true);
    // Port bore port_ibic_ft_45
    translate([150.967, 150.967, -105.000]) rotate([0.000, 90.000, 45.000]) cylinder(d=63.500, h=67.000, center=true);
    // Port bore port_ibic_ft_315
    translate([150.967, -150.967, -105.000]) rotate([0.000, 90.000, 315.000]) cylinder(d=63.500, h=67.000, center=true);
    // Port bore port_interf_x_0
    translate([211.000, 0.000, -133.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=28.000, h=62.000, center=true);
    // Port bore port_interf_y_90
    translate([0.000, 211.000, -133.000]) rotate([0.000, 90.000, 90.000]) cylinder(d=28.000, h=62.000, center=true);
    // Port bore port_interf_z_270
    translate([-0.000, -211.000, -133.000]) rotate([0.000, 90.000, 270.000]) cylinder(d=28.000, h=62.000, center=true);
    // Port bore port_gauge_rga_225
    translate([-150.967, -150.967, -105.000]) rotate([0.000, 90.000, 225.000]) cylinder(d=38.000, h=67.000, center=true);
    // Port bore port_fiducial_50
    translate([135.628, 161.635, 9.000]) rotate([0.000, 90.000, 50.000]) cylinder(d=32.000, h=62.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S5_1_01();

part_S5_1_01();
