

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toHexString(input_1_0);
        String output_2 = Double.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("0x1.566d8c1e813p100") && output_2.equals("0x1.23c92a375adc6p-71")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

