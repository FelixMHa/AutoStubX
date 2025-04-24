

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toString(input_1_0);
        String output_2 = Double.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("1.7920279439427622E-96") && output_2.equals("-2.1167737922197866E9")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

