// Direct ISIS C++ benchmark executable for PyISIS comparison.

#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <QString>

#include "Camera.h"
#include "ControlMeasure.h"
#include "ControlNet.h"
#include "ControlPoint.h"
#include "Cube.h"
#include "IException.h"

namespace {

struct Options {
  std::string mode;
  std::string label;
  std::string cube_path;
  std::string net_path;
  std::string output_path;
  int sample_step = 10;
  int line_step = 10;
  int max_points = 0;
};

struct CameraSample {
  int index;
  double sample;
  double line;
};

struct CameraPointRecord {
  int index;
  double input_sample;
  double input_line;
  double latitude;
  double longitude;
  double roundtrip_sample;
  double roundtrip_line;
};

double elapsed_seconds(std::chrono::steady_clock::time_point start) {
  return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

std::string qstring_to_string(const QString &value) {
  return value.toStdString();
}

std::string escape_json(const std::string &value) {
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char ch : value) {
    switch (ch) {
      case '"':
        out << "\\\"";
        break;
      case '\\':
        out << "\\\\";
        break;
      case '\b':
        out << "\\b";
        break;
      case '\f':
        out << "\\f";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        if (ch < 0x20) {
          out << "\\u" << std::setw(4) << static_cast<int>(ch);
        } else {
          out << static_cast<char>(ch);
        }
        break;
    }
  }
  return out.str();
}

void require_value(int &index, int argc, char **argv, const std::string &flag) {
  if (index + 1 >= argc) {
    throw std::runtime_error(flag + " requires a value");
  }
}

int parse_positive_int(const std::string &value, const std::string &flag) {
  size_t parsed = 0;
  int result = std::stoi(value, &parsed);
  if (parsed != value.size() || result <= 0) {
    throw std::runtime_error(flag + " must be a positive integer");
  }
  return result;
}

Options parse_options(int argc, char **argv) {
  if (argc < 2) {
    throw std::runtime_error("usage: isis_cpp_benchmark <camera|controlnet> [options]");
  }

  Options options;
  options.mode = argv[1];
  for (int i = 2; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--label") {
      require_value(i, argc, argv, arg);
      options.label = argv[++i];
    } else if (arg == "--cube") {
      require_value(i, argc, argv, arg);
      options.cube_path = argv[++i];
    } else if (arg == "--net") {
      require_value(i, argc, argv, arg);
      options.net_path = argv[++i];
    } else if (arg == "--output") {
      require_value(i, argc, argv, arg);
      options.output_path = argv[++i];
    } else if (arg == "--sample-step") {
      require_value(i, argc, argv, arg);
      options.sample_step = parse_positive_int(argv[++i], arg);
    } else if (arg == "--line-step") {
      require_value(i, argc, argv, arg);
      options.line_step = parse_positive_int(argv[++i], arg);
    } else if (arg == "--max-points") {
      require_value(i, argc, argv, arg);
      options.max_points = parse_positive_int(argv[++i], arg);
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }

  if (options.mode != "camera" && options.mode != "controlnet") {
    throw std::runtime_error("mode must be camera or controlnet");
  }
  if (options.label.empty()) {
    throw std::runtime_error("--label is required");
  }
  if (options.output_path.empty()) {
    throw std::runtime_error("--output is required");
  }
  return options;
}

std::vector<int> axis_positions(int count, int step, const std::string &name) {
  if (count <= 0) {
    throw std::runtime_error(name + " count must be positive");
  }
  if (step <= 0) {
    throw std::runtime_error(name + " step must be positive");
  }

  std::vector<int> positions;
  for (int position = 1; position <= count; position += step) {
    positions.push_back(position);
  }
  if (positions.back() != count) {
    positions.push_back(count);
  }
  return positions;
}

std::vector<CameraSample> generate_camera_samples(
    int sample_count,
    int line_count,
    int sample_step,
    int line_step,
    int max_points) {
  std::vector<CameraSample> samples;
  const std::vector<int> sample_positions = axis_positions(sample_count, sample_step, "sample");
  const std::vector<int> line_positions = axis_positions(line_count, line_step, "line");
  for (int line : line_positions) {
    for (int sample : sample_positions) {
      samples.push_back(CameraSample{
          static_cast<int>(samples.size()),
          static_cast<double>(sample),
          static_cast<double>(line),
      });
      if (max_points > 0 && static_cast<int>(samples.size()) >= max_points) {
        return samples;
      }
    }
  }
  return samples;
}

std::ofstream open_output(const std::string &path) {
  std::ofstream out(path);
  if (!out) {
    throw std::runtime_error("failed to open output path: " + path);
  }
  out << std::setprecision(17);
  return out;
}

void write_camera_result(const Options &options) {
  if (options.cube_path.empty()) {
    throw std::runtime_error("--cube is required for camera mode");
  }

  Isis::Cube cube;
  cube.open(QString::fromStdString(options.cube_path), "r");
  Isis::Camera *camera = cube.camera();
  const std::vector<CameraSample> samples = generate_camera_samples(
      camera->Samples(),
      camera->Lines(),
      options.sample_step,
      options.line_step,
      options.max_points);

  int failed_set_image_count = 0;
  int failed_set_universal_ground_count = 0;
  double core_seconds = 0.0;
  std::vector<CameraPointRecord> point_records;
  point_records.reserve(samples.size());

  for (const CameraSample &sample : samples) {
    const auto operation_start = std::chrono::steady_clock::now();
    if (!camera->SetImage(sample.sample, sample.line)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_set_image_count;
      continue;
    }

    const double latitude = camera->UniversalLatitude();
    const double longitude = camera->UniversalLongitude();
    if (!camera->SetUniversalGround(latitude, longitude)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_set_universal_ground_count;
      continue;
    }

    const double roundtrip_sample = camera->Sample();
    const double roundtrip_line = camera->Line();
    core_seconds += elapsed_seconds(operation_start);
    point_records.push_back(CameraPointRecord{
        sample.index,
        sample.sample,
        sample.line,
        latitude,
        longitude,
        roundtrip_sample,
        roundtrip_line,
    });
  }
  cube.close();

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"camera\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"cube_path\": \"" << escape_json(options.cube_path) << "\",\n"
      << "  \"input_point_count\": " << samples.size() << ",\n"
      << "  \"successful_point_count\": " << point_records.size() << ",\n"
      << "  \"failed_set_image_count\": " << failed_set_image_count << ",\n"
      << "  \"failed_set_universal_ground_count\": " << failed_set_universal_ground_count << ",\n"
      << "  \"first_point_index\": ";
  if (samples.empty()) {
    out << "null";
  } else {
    out << samples.front().index;
  }
  out << ",\n"
      << "  \"core_seconds\": " << core_seconds << ",\n"
      << "  \"average_successful_point_seconds\": ";
  if (point_records.empty()) {
    out << "null";
  } else {
    out << core_seconds / static_cast<double>(point_records.size());
  }
  out << ",\n"
      << "  \"points\": [\n";
  for (size_t i = 0; i < point_records.size(); ++i) {
    const CameraPointRecord &point = point_records[i];
    if (i > 0) {
      out << ",\n";
    }
    out << "    {\"index\": " << point.index
        << ", \"input_sample\": " << point.input_sample
        << ", \"input_line\": " << point.input_line
        << ", \"latitude\": " << point.latitude
        << ", \"longitude\": " << point.longitude
        << ", \"roundtrip_sample\": " << point.roundtrip_sample
        << ", \"roundtrip_line\": " << point.roundtrip_line
        << "}";
  }
  out << "\n  ]\n"
      << "}\n";
}

void write_controlnet_result(const Options &options) {
  if (options.net_path.empty()) {
    throw std::runtime_error("--net is required for controlnet mode");
  }

  const auto load_start = std::chrono::steady_clock::now();
  Isis::ControlNet control_net(QString::fromStdString(options.net_path));
  const double load_seconds = elapsed_seconds(load_start);

  int measure_count = 0;
  std::map<std::string, int> serial_measure_counts;
  const auto traverse_start = std::chrono::steady_clock::now();
  const int point_count = control_net.GetNumPoints();
  for (int point_index = 0; point_index < point_count; ++point_index) {
    Isis::ControlPoint *point = control_net.GetPoint(point_index);
    (void)point->GetId();
    (void)point->GetPointTypeString();
    (void)point->IsIgnored();
    (void)point->IsEditLocked();

    const int point_measure_count = point->GetNumMeasures();
    for (int measure_index = 0; measure_index < point_measure_count; ++measure_index) {
      Isis::ControlMeasure *measure = point->GetMeasure(measure_index);
      ++measure_count;

      const std::string serial = qstring_to_string(measure->GetCubeSerialNumber());
      (void)measure->GetSample();
      (void)measure->GetLine();
      (void)measure->GetMeasureTypeString();
      (void)measure->IsIgnored();
      (void)measure->IsEditLocked();

      if (!serial.empty()) {
        serial_measure_counts[serial] += 1;
      }
    }
  }
  const double traverse_seconds = elapsed_seconds(traverse_start);

  const int valid_point_count = control_net.GetNumValidPoints();
  const int valid_measure_count = control_net.GetNumValidMeasures();

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"controlnet\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"net_path\": \"" << escape_json(options.net_path) << "\",\n"
      << "  \"point_count\": " << point_count << ",\n"
      << "  \"measure_count\": " << measure_count << ",\n"
      << "  \"valid_point_count\": " << valid_point_count << ",\n"
      << "  \"valid_measure_count\": " << valid_measure_count << ",\n"
      << "  \"serial_measure_counts\": {";
  bool first_serial = true;
  for (const auto &entry : serial_measure_counts) {
    if (!first_serial) {
      out << ", ";
    }
    first_serial = false;
    out << "\"" << escape_json(entry.first) << "\": " << entry.second;
  }
  out << "},\n"
      << "  \"load_seconds\": " << load_seconds << ",\n"
      << "  \"traverse_seconds\": " << traverse_seconds << ",\n"
      << "  \"core_seconds\": " << load_seconds + traverse_seconds << "\n"
      << "}\n";
}

}  // namespace

int main(int argc, char **argv) {
  try {
    const Options options = parse_options(argc, argv);
    if (options.mode == "camera") {
      write_camera_result(options);
    } else {
      write_controlnet_result(options);
    }
    return EXIT_SUCCESS;
  } catch (const Isis::IException &error) {
    std::cerr << error.toString().toStdString() << std::endl;
  } catch (const std::exception &error) {
    std::cerr << error.what() << std::endl;
  }
  return EXIT_FAILURE;
}
