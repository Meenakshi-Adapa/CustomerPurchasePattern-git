
import java.io.IOException;
import java.util.Locale;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.DoubleWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

public class CountryRevenue {

    public static class RevenueMapper
            extends Mapper<Object, Text, Text, DoubleWritable> {

        private final Text country = new Text();
        private final DoubleWritable revenue = new DoubleWritable();

        @Override
        public void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {

            String line = value.toString();

            // Skip blank lines.
            if (line.trim().isEmpty()) {
                return;
            }

            // Parse CSV fields, including quoted fields containing commas.
            java.util.List<String> fields = parseCsvLine(line);

            // Expected columns:
            // 0 InvoiceNo, 1 StockCode, 2 Description, 3 Quantity,
            // 4 InvoiceDate, 5 UnitPrice, 6 CustomerID, 7 Country.
            if (fields.size() < 8) {
                context.getCounter("CSV", "MALFORMED_ROWS").increment(1);
                return;
            }

            try {
                double quantity = Double.parseDouble(fields.get(3).trim());
                double unitPrice = Double.parseDouble(fields.get(5).trim());
                String countryName = fields.get(7).trim();

                if (countryName.isEmpty()) {
                    context.getCounter("CSV", "EMPTY_COUNTRY").increment(1);
                    return;
                }

                // Ignore rows with non-positive prices or zero quantities.
                // Negative quantities (returns) are retained.
                if (unitPrice <= 0 || quantity == 0) {
                    context.getCounter("CSV", "IGNORED_ROWS").increment(1);
                    return;
                }

                country.set(countryName);
                revenue.set(quantity * unitPrice);
                context.write(country, revenue);

            } catch (NumberFormatException e) {
                context.getCounter("CSV", "INVALID_NUMERIC_ROWS").increment(1);
            }
        }

        private static java.util.List<String> parseCsvLine(String line) {
            java.util.List<String> fields = new java.util.ArrayList<>();
            StringBuilder field = new StringBuilder();
            boolean inQuotes = false;

            for (int i = 0; i < line.length(); i++) {
                char c = line.charAt(i);

                if (c == '"') {
                    if (inQuotes && i + 1 < line.length()
                            && line.charAt(i + 1) == '"') {
                        field.append('"');
                        i++;
                    } else {
                        inQuotes = !inQuotes;
                    }
                } else if (c == ',' && !inQuotes) {
                    fields.add(field.toString());
                    field.setLength(0);
                } else {
                    field.append(c);
                }
            }

            fields.add(field.toString());
            return fields;
        }
    }

    public static class RevenueReducer
            extends Reducer<Text, DoubleWritable, Text, DoubleWritable> {

        private final DoubleWritable totalRevenue = new DoubleWritable();

        @Override
        public void reduce(Text country, Iterable<DoubleWritable> values,
                           Context context)
                throws IOException, InterruptedException {

            double total = 0.0;

            for (DoubleWritable value : values) {
                total += value.get();
            }

            totalRevenue.set(total);
            context.write(country, totalRevenue);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println(
                "Usage: CountryRevenue <input path> <output path>");
            System.exit(2);
        }

        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "Revenue by Country");

        job.setJarByClass(CountryRevenue.class);
        job.setMapperClass(RevenueMapper.class);
        job.setCombinerClass(RevenueReducer.class);
        job.setReducerClass(RevenueReducer.class);

        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(DoubleWritable.class);

        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
